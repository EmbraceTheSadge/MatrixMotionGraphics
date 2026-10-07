"""Measure the chosen take and write the timing that drives ALL animation.

  python timing.py <project> --take seed131 [--end 35.6] [--bpm 140] [--fps 30] [--per-bar 4]

Reads   <project>/audio/song.json (bpm, lyrics, mode, drop_window, fps)
        <project>/audio/takes/<take>.wav
        <project>/audio/stems/htdemucs/<take>/{vocals,no_vocals}.wav + transcript.json   (from stems.sh, optional)
Writes  <project>/audio/timing.json and <project>/assets/js/timing.js  (window.TIMING = {...})

timing.json: duration (= musical end, or --end), bpm, beat_period, first_beat, beats, downbeats,
drop, novelty (candidate section changes, snapped to downbeats), sections, lines + words (every lyric
word with its sung onset and a `src` flag), drum_hits, loudness_db_per_s, env (mix/kick/snare/vocal/inst
envelopes 0..1 at env_fps).

Word `src`: exact / fuzzy / subst = heard by the recogniser (subst = misheard but in the right place),
interp = placed between heard neighbours, token-fill = an unheard line mapped onto the recogniser's
leftover (misheard) tokens in that gap, onset-fill = mapped onto the vocal stem's onsets phrase by phrase,
even-fill = spread evenly over the phrase (no onsets found). Check every onset-fill / even-fill word in the report.
Lines the singer never sang are listed as "unsung" and left out.
"""

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audiolib as A  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--take", required=True)
ap.add_argument("--end", type=float)
ap.add_argument("--bpm", type=float)
ap.add_argument("--fps", type=int)
ap.add_argument("--per-bar", type=int, default=4)
args = ap.parse_args()

P = os.path.abspath(args.project)
take = args.take.replace(".wav", "")
cfg_path = os.path.join(P, "audio", "song.json")
CFG = json.load(open(cfg_path)) if os.path.exists(cfg_path) else {}
FPS = args.fps or int(CFG.get("fps", 30))
stem_dir = os.path.join(P, "audio", "stems", "htdemucs", take)
has_stems = os.path.exists(os.path.join(stem_dir, "no_vocals.wav"))

mix = A.load(os.path.join(P, "audio", "takes", take + ".wav"))
inst = A.load(os.path.join(stem_dir, "no_vocals.wav")) if has_stems else mix
voc = A.load(os.path.join(stem_dir, "vocals.wav")) if has_stems else None
raw_dur = len(mix) / A.SR
END = round(args.end or A.musical_end(mix), 3)

# ---- beat grid (on the instrumental stem when we have it: drums without the vocal)
mag, ofps = A.stft_mag(inst)
full = A.band_flux(mag, 30, 11000)
kick = A.band_flux(mag, 30, 150)
snare = A.band_flux(mag, 1500, 5000)
hint = args.bpm or CFG.get("bpm")
est = A.fold_bpm(A.tempo_autocorr(full, ofps), hint)
bpm, beats = A.beat_grid(full, ofps, raw_dur, hint or est)
beats = beats[beats <= END + 0.01]
# the drop almost always lands on a downbeat, so it decides which beat is "1" (kick voting alone
# gets breakbeats wrong); without a clear drop, the kick decides
lo, hi = CFG.get("drop_window", [END * 0.2, END * 0.9])
drop_t, drop_jump = A.find_drop(mix, lo, hi)
anchor = float(beats[np.argmin(np.abs(beats - drop_t))]) if drop_t is not None and drop_jump >= 3 and len(beats) else None
downbeats, slot = A.downbeats_from_kick(beats, kick, ofps, args.per_bar, anchor)
period = 60.0 / bpm


def snap_down(t):
    return float(downbeats[np.argmin(np.abs(downbeats - t))]) if len(downbeats) else t


drop = round(anchor, 3) if anchor is not None else None
novelty = sorted({round(snap_down(t), 3) for t in A.novelty_boundaries(mix) if t < END})

# ---- lyrics -> word onsets
lines_out, words_out, unsung = [], [], []
MODE = CFG.get("mode", "score" if CFG.get("instrumental") else "song")
lyr = A.parse_lyrics(CFG.get("lyrics", "")) if MODE == "song" and not CFG.get("instrumental") else []
tx_path = os.path.join(stem_dir, "transcript.json")
if lyr and not os.path.exists(tx_path):
    print("NOTE: no vocal-stem transcript; run stems.sh first to time the lyrics.", file=sys.stderr)
if lyr and os.path.exists(tx_path):
    heard = [h for h in A.load_transcript(tx_path) if h["start"] < END]
    flat = [(li, wi, w) for li, ln in enumerate(lyr) for wi, w in enumerate(ln["words"])]
    al = A.align([A.norm_word(w) for _, _, w in flat], heard)
    on_t, on_s, phrases = A.vocal_onsets(os.path.join(stem_dir, "vocals16k.wav") if os.path.exists(os.path.join(stem_dir, "vocals16k.wav")) else os.path.join(stem_dir, "vocals.wav"))
    T = [heard[j]["start"] if j is not None else None for j, _ in al]
    SRC = [k if j is not None else None for j, k in al]

    # 1. lines with some heard words: interpolate the gaps inside the line
    for li, ln in enumerate(lyr):
        idx = [k for k, (l2, _, _) in enumerate(flat) if l2 == li]
        known = [k for k in idx if T[k] is not None]
        if not known:
            continue
        for k in idx:
            if T[k] is not None:
                continue
            prev = max([q for q in known if q < k], default=None)
            nxt = min([q for q in known if q > k], default=None)
            if prev is not None and nxt is not None:
                span = sum(len(flat[q][2]) for q in range(prev, nxt))
                done = sum(len(flat[q][2]) for q in range(prev, k))
                T[k] = T[prev] + (T[nxt] - T[prev]) * done / max(span, 1)
            elif prev is not None:
                T[k] = T[prev] + 0.25 * (k - prev)
            else:
                T[k] = T[nxt] - 0.25 * (nxt - k)
            SRC[k] = "interp"

    # 2. runs of fully unheard lines: map onto vocal onsets in the gap, in order
    li = 0
    while li < len(lyr):
        if any(T[k] is not None for k, (l2, _, _) in enumerate(flat) if l2 == li):
            li += 1
            continue
        run = [li]
        while run[-1] + 1 < len(lyr) and not any(T[k] is not None for k, (l2, _, _) in enumerate(flat) if l2 == run[-1] + 1):
            run.append(run[-1] + 1)
        ks = [k for k, (l2, _, _) in enumerate(flat) if l2 in run]
        before = [T[k] for k in range(ks[0]) if T[k] is not None]
        after = [T[k] for k in range(ks[-1] + 1, len(flat)) if T[k] is not None]
        a = (before[-1] + 0.15) if before else 0.0
        b = (after[0] - 0.08) if after else END
        used = {j for j, _ in al if j is not None}
        spare = [h for j, h in enumerate(heard) if j not in used and a <= h["start"] < b]
        if spare and not (not after and len(spare) < len(ks) // 2):
            # the recogniser heard SOMETHING here, just not the lyric ("something else should insert"
            # for "type it out, hit enter"): same syllables, same onsets, so map the words onto those tokens
            for n, k in enumerate(ks):
                h = spare[round(n * (len(spare) - 1) / max(len(ks) - 1, 1))]
                T[k], SRC[k] = h["start"], "token-fill"
        else:
            # map each line onto a voiced phrase, then each word onto that phrase's strongest onsets
            ph = [p for p in phrases if p[0] >= a - 0.05 and p[0] < b]
            while len(ph) > len(run):
                gaps = [ph[i + 1][0] - ph[i][1] for i in range(len(ph) - 1)]
                i = int(np.argmin(gaps))
                ph[i:i + 2] = [(ph[i][0], ph[i + 1][1])]
            if ph and (after or len(ph) == len(run)):
                groups = [[k for k in ks if flat[k][0] == r] for r in run] if len(ph) == len(run) else [ks]
                spans = ph if len(ph) == len(run) else [(ph[0][0], ph[-1][1])]
                for g, (p0, p1) in zip(groups, spans):
                    # walk an even grid across the phrase; each word takes the strongest onset in its slot
                    p0, p1 = max(a, p0), min(b, p1 + 0.2)
                    slot_w = (p1 - p0) / len(g)
                    last = p0 - 1.0
                    for n, k in enumerate(g):
                        sel = np.where((on_t >= p0 + slot_w * (n - 0.35)) & (on_t < p0 + slot_w * (n + 0.65)) & (on_t > last + 0.06))[0]
                        if len(sel):
                            T[k], SRC[k] = float(on_t[sel[np.argmax(on_s[sel])]]), "onset-fill"
                        else:
                            T[k], SRC[k] = max(last + 0.08, p0 + slot_w * n), "even-fill"
                        last = T[k]
            else:
                unsung += [lyr[r]["text"] for r in run]
        li = run[-1] + 1

    # 3. snap heard/interpolated words to the strongest vocal onset close by
    for k in range(len(flat)):
        if T[k] is None or SRC[k] == "onset-fill":
            continue
        m = (on_t >= T[k] - 0.12) & (on_t <= T[k] + 0.10)
        if m.any():
            cand = np.where(m)[0]
            T[k] = float(on_t[cand[np.argmax(on_s[cand] - 2.0 * np.abs(on_t[cand] - T[k]))]])

    for li, ln in enumerate(lyr):
        lw = [{"word": w, "t": round(T[k], 3), "line": li, "src": SRC[k]} for k, (l2, _, w) in enumerate(flat) if l2 == li and T[k] is not None]
        if not lw:
            continue
        for i in range(1, len(lw)):
            if lw[i]["t"] <= lw[i - 1]["t"] + 0.06:
                lw[i]["t"] = round(lw[i - 1]["t"] + 0.08, 3)
        for i, w in enumerate(lw):
            w["end"] = lw[i + 1]["t"] if i + 1 < len(lw) else None
        lines_out.append({"i": li, "section": ln["section"], "text": ln["text"], "start": lw[0]["t"], "words": [w["word"] for w in lw]})
        words_out += lw
    lines_out.sort(key=lambda l: l["start"])
    for n, ln in enumerate(lines_out):
        last = [w for w in words_out if w["line"] == ln["i"]][-1]
        nxt = lines_out[n + 1]["start"] if n + 1 < len(lines_out) else END
        last["end"] = round(min(nxt, last["t"] + 1.2), 3)
        ln["end"] = last["end"]

# ---- sections: from the lyric tags when there are words, else from novelty boundaries
sections = []
if lines_out:
    for ln in lines_out:
        if not sections or sections[-1]["name"] != ln["section"]:
            sections.append({"name": ln["section"], "start": ln["start"]})
    sections[0]["start"] = 0.0
else:
    cuts = [0.0] + [t for t in novelty if 1.0 < t < END - 1.0]
    sections = [{"name": f"part{i + 1}", "start": t} for i, t in enumerate(cuts)]
for i, s in enumerate(sections):
    s["end"] = sections[i + 1]["start"] if i + 1 < len(sections) else END

# ---- envelopes + hits + loudness
dur_frames = int(END * FPS) + 1
env = {"mix": A.rms_env(mix, FPS), "kick": A.onset_env(kick, ofps, raw_dur, FPS), "snare": A.onset_env(snare, ofps, raw_dur, FPS)}
if voc is not None:
    env["vocal"] = A.rms_env(voc, FPS)
    env["inst"] = A.rms_env(inst, FPS)
env = {k: [round(float(v), 3) for v in a[:dur_frames]] for k, a in env.items()}
loud = A.loudness_per_s(mix)[: int(np.ceil(END))]

timing = {
    "take": take,
    "title": CFG.get("title", ""),
    "duration": END,
    "raw_duration": round(raw_dur, 3),
    "bpm": round(bpm, 3),
    "beat_period": round(period, 5),
    "first_beat": round(float(beats[0]), 3) if len(beats) else 0.0,
    "beats": [round(float(b), 3) for b in beats],
    "downbeats": [round(float(d), 3) for d in downbeats],
    "drop": drop,
    "drop_jump_db": drop_jump,
    "novelty": novelty,
    "sections": sections,
    "lines": lines_out,
    "words": words_out,
    "unsung_lines": unsung,
    "drum_hits": A.drum_hits(inst, END),
    "loudness_db_per_s": [round(float(v), 1) for v in loud],
    "env_fps": FPS,
    "env": env,
}
os.makedirs(os.path.join(P, "audio"), exist_ok=True)
json.dump(timing, open(os.path.join(P, "audio", "timing.json"), "w"), indent=1)
os.makedirs(os.path.join(P, "assets", "js"), exist_ok=True)
with open(os.path.join(P, "assets", "js", "timing.js"), "w") as f:
    f.write("/* generated from audio/timing.json by motion-studio timing.py: do not edit */\n")
    f.write("window.TIMING = " + json.dumps(timing, separators=(",", ":")) + ";\n")

# ---- report
print(f"{take}: {timing['bpm']} BPM, beat {timing['beat_period']}s, first beat {timing['first_beat']}, downbeat slot {slot}")
print(f"duration {END}s (raw {raw_dur:.2f}s{'' if args.end else ', musical end detected'}); drop {drop} (+{drop_jump} dB)")
print("downbeats:", " ".join(f"{d:.3f}" for d in timing["downbeats"][:24]), "..." if len(timing["downbeats"]) > 24 else "")
print("sections:", " | ".join(f"{s['name']} {s['start']:.2f}-{s['end']:.2f}" for s in sections))
print("energy/s:", A.energy_string(mix)[: int(np.ceil(END))])
if words_out:
    flag = {"token-fill", "onset-fill", "even-fill", "subst", "interp"}
    for ln in lines_out:
        ws = [w for w in words_out if w["line"] == ln["i"]]
        marks = " ".join(f"{w['word']}@{w['t']:.2f}{'*' if w['src'] in flag else ''}" for w in ws)
        print(f"  [{ln['section']}] {marks}")
    print("  * = not heard verbatim (subst / interp / token-fill / onset-fill / even-fill): sanity-check these")
if unsung:
    print("unsung lines (left out):", " / ".join(unsung))
print(f"wrote {os.path.join(P, 'audio', 'timing.json')} and assets/js/timing.js")
