"""Rank song / score takes without listening.

  python rank_takes.py <project> [seed11 seed23 ...]      (default: every audio/takes/seed*.wav)

Song mode (song.json "mode": "song"): how much of the lyric sheet is actually sung, in order (from the
VOCAL-STEM transcript that stems.sh writes; run it on every take first), steady tempo, energy contrast,
and whether the music lasts long enough.
Score mode ("mode": "score"): fit of the loudness curve to the story arc (song.json "arc": [[t, 0..1], ...]),
a clear drop inside "drop_window", a quiet start and a resolving tail.

Both modes penalise a take whose music stops early (one take scored 0.83 on lyrics but went silent
at 29 s of 38). Writes audio/takes/ranking.json. Listen to the top two if you can; the numbers are a
shortlist, not taste.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audiolib as A  # noqa: E402

P = os.path.abspath(sys.argv[1])
CFG = json.load(open(os.path.join(P, "audio", "song.json")))
TAKES = os.path.join(P, "audio", "takes")
names = [n.replace(".wav", "") for n in sys.argv[2:]] or sorted(
    f[:-4] for f in os.listdir(TAKES) if f.startswith("seed") and f.endswith(".wav")
)
MODE = CFG.get("mode", "score" if CFG.get("instrumental") else "song")
TARGET = float(CFG.get("target_duration", float(CFG["duration"]) - 2))
HINT = CFG.get("bpm")
sheet = [A.norm_word(w) for ln in A.parse_lyrics(CFG.get("lyrics", "")) for w in ln["words"]]


def arc_curve(n):
    pts = CFG.get("arc") or [[0, 0.1], [0.15, 0.25], [0.45, 0.6], [0.68, 0.75], [0.7, 1.0], [0.85, 0.95], [1.0, 0.15]]
    if all(p[0] <= 1.0 for p in pts):  # fractions of the target length
        pts = [[p[0] * TARGET, p[1]] for p in pts]
    xs, ys = zip(*pts)
    return np.interp(np.arange(n), xs, ys)


rows = []
for name in names:
    x = A.load(os.path.join(TAKES, name + ".wav"))
    dur = len(x) / A.SR
    end = A.musical_end(x)
    sustain = min(A.sustain_end(x), end)
    drift, bpm = A.tempo_drift(x)
    bpm = round(A.fold_bpm(bpm, HINT), 1)
    r = {"take": name, "dur": round(dur, 2), "musical_end": end, "sustain_end": sustain, "bpm": bpm, "tempo_drift": drift, "energy_per_s": A.energy_string(x)}
    lo, hi = CFG.get("drop_window", [TARGET * 0.2, TARGET * 0.9])
    drop_t, jump = A.find_drop(x, lo, hi)
    r["drop_t"], r["drop_jump_db"] = (round(drop_t, 2) if drop_t is not None else None), jump
    sec = A.loudness_per_s(x)[: int(min(end, len(x) / A.SR))]
    peak = sec.max() if len(sec) else 0
    r["intro_vs_peak_db"] = round(float(sec[:5].mean() - peak), 1) if len(sec) >= 5 else 0.0
    r["tail_vs_peak_db"] = round(float(sec[-6:].mean() - peak), 1) if len(sec) >= 6 else 0.0
    score = 0.0
    if MODE == "song":
        tx = os.path.join(P, "audio", "stems", "htdemucs", name, "transcript.json")
        if sheet and os.path.exists(tx):
            heard = A.load_transcript(tx)
            al = A.align(sheet, heard)
            r["lyric_match"] = round(sum(1 for j, k in al if k in ("exact", "fuzzy")) / len(sheet), 2)
            r["heard"] = " ".join(h["norm"] for h in heard)
            score += 10 * r["lyric_match"]
        else:
            r["lyric_match"] = None
        score += 0.35 * min(max(jump, 0), 12)  # a drop / break gives the visuals somewhere to explode
        if sustain < TARGET - 3:
            score -= 3
            r["warning"] = f"band thins out at {sustain}s"
    else:
        lo_db, hi_db = np.percentile(sec, 5), np.percentile(sec, 98)
        normd = np.clip((sec - lo_db) / (hi_db - lo_db + 1e-6), 0, 1)
        r["arc_fit"] = round(float(np.corrcoef(normd, arc_curve(len(normd)))[0, 1]), 3) if len(normd) > 3 else 0.0
        score += r["arc_fit"] * 10 + min(max(jump, 0), 12) * 0.6
        score += min(-r["intro_vs_peak_db"], 24) * 0.15 + min(-r["tail_vs_peak_db"], 24) * 0.1
        if drop_t is None or jump < 4:
            score -= 3
    if end < TARGET - 1:
        score -= 3
        r["warning"] = (r.get("warning", "") + f" music stops at {end}s (< target {TARGET}s)").strip()
    if drift > 2:
        score -= 2
    r["score"] = round(score, 2)
    rows.append(r)

rows.sort(key=lambda r: -r["score"])
json.dump({"mode": MODE, "target_duration": TARGET, "ranking": rows}, open(os.path.join(TAKES, "ranking.json"), "w"), indent=1)
print(f"mode: {MODE}   target length: {TARGET}s   (higher score = better)")
for r in rows:
    extra = f"lyrics {r['lyric_match']}" if MODE == "song" else f"arc fit {r['arc_fit']:+.2f}"
    print(f"{r['score']:6.2f}  {r['take']:9s} {extra:12s} bpm {r['bpm']:6.1f} (drift {r['tempo_drift']})  "
          f"ends {r['musical_end']:5.1f}s (full band to {r['sustain_end']:.1f}s)  drop {r['drop_t']}s +{r['drop_jump_db']}dB  {r.get('warning', '')}")
    print(f"         energy/s {r['energy_per_s']}")
if MODE == "song" and any(r["lyric_match"] is None for r in rows):
    print("\nlyric_match is missing for some takes: run scripts/music/stems.sh on them first (vocal stem + transcript).")
print(f"\nwrote {os.path.join(TAKES, 'ranking.json')}")
