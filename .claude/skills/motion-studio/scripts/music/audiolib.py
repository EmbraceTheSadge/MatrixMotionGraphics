"""Shared audio analysis for motion-studio (numpy + ffmpeg only, deterministic).

Beat grid, downbeats, loudness, musical end, drop detection, section novelty, 30/60 fps envelopes,
drum hits, vocal onsets, lyric-sheet parsing and lyric-to-transcript alignment.
"""

import difflib
import json
import os
import re
import subprocess

import numpy as np

SR = 22050


# ----------------------------------------------------------------------------- loading


def load(path, sr=SR):
    raw = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
        capture_output=True,
        check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def stft_mag(x, n=1024, hop=256, sr=SR):
    win = np.hanning(n)
    if len(x) < n:
        x = np.pad(x, (0, n - len(x)))
    frames = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * win
    return np.abs(np.fft.rfft(frames, axis=1)), sr / hop


def band_flux(mag, lo_hz, hi_hz, n=1024, sr=SR):
    freqs = np.fft.rfftfreq(n, 1 / sr)
    m = mag[:, (freqs >= lo_hz) & (freqs < hi_hz)]
    d = np.diff(m, axis=0, prepend=m[:1])
    return np.maximum(d, 0).sum(axis=1)


# ----------------------------------------------------------------------------- loudness / shape


def loudness_per_s(x, sr=SR):
    """dB RMS per whole second."""
    n = int(len(x) / sr)
    return np.array([20 * np.log10(np.sqrt(np.mean(x[i * sr : (i + 1) * sr] ** 2)) + 1e-6) for i in range(max(n, 1))])


def loudness_curve(x, hop_s=0.25, sr=SR):
    hop = int(sr * hop_s)
    win = hop * 2
    vals = [20 * np.log10(np.sqrt(np.mean(x[i : i + win] ** 2)) + 1e-6) for i in range(0, max(1, len(x) - win), hop)]
    return np.array(vals), hop_s


def energy_string(x, sr=SR):
    """One digit 0-9 per second: a quick picture of the take's energy over time."""
    blk = sr
    env = np.array([np.sqrt(np.mean(x[i : i + blk] ** 2)) for i in range(0, len(x), blk)])
    return "".join(str(min(9, int(9.99 * e / (env.max() + 1e-9)))) for e in env)


def musical_end(x, sr=SR, below_db=30.0):
    """Last moment the music is still playing: loudness within `below_db` of the loudest second.
    Catches takes whose music stops early and then idles in silence or noise."""
    curve, hop_s = loudness_curve(x, 0.1, sr)
    if len(curve) == 0:
        return len(x) / sr
    ref = np.percentile(curve, 95)
    alive = np.where(curve > ref - below_db)[0]
    if len(alive) == 0:
        return len(x) / sr
    return round(min(len(x) / sr, (alive[-1] + 2) * hop_s), 2)


def sustain_end(x, sr=SR, below_db=12.0, span_s=3):
    """Last moment the band is still really PLAYING: the rolling 3 s RMS stays within `below_db` of
    the loud part. A song whose sustain_end is far before its musical_end thinned out to a quiet
    bed (the take "stopped early", even if a few hits ring on)."""
    e = np.array([np.sqrt(np.mean(x[i : i + sr] ** 2)) for i in range(0, len(x) - sr // 2, sr)])
    if len(e) <= span_s:
        return round(len(x) / sr, 2)
    roll = np.convolve(e, np.ones(span_s) / span_s, "valid")  # roll[i] = mean of seconds i..i+span-1
    ok = np.where(roll >= np.percentile(e, 90) * 10 ** (-below_db / 20))[0]
    return round(float(min(len(x) / sr, ok[-1] + span_s)) if len(ok) else 0.0, 2)


def find_drop(x, lo_s, hi_s, sr=SR, before_s=1.0, after_s=2.0):
    """The drop: the sharpest rise in loudness (mean of the next `after_s` vs the last `before_s`)
    INTO a loud sustained section (the next 6 s count too, so a final slam into the fade-out loses),
    with the jump point inside [lo_s, hi_s]. Returns (time, jump in dB)."""
    hop_s = 0.05
    hop, win = int(sr * hop_s), int(sr * 0.1)
    curve = np.array([20 * np.log10(np.sqrt(np.mean(x[i : i + win] ** 2)) + 1e-6) for i in range(0, max(1, len(x) - win), hop)])
    kb, ka, ks = int(before_s / hop_s), int(after_s / hop_s), int(6.0 / hop_s)
    ref = np.percentile(curve, 95)
    best, best_jump, best_t = -1e9, 0.0, None
    for i in range(max(kb, int(lo_s / hop_s)), min(len(curve) - ka, int(hi_s / hop_s) + 1)):
        jump = curve[i : i + ka].mean() - curve[i - kb : i].mean()
        score = jump + 1.5 * (curve[i : i + ks].mean() - ref)
        if score > best:
            best, best_jump, best_t = score, jump, i * hop_s
    return best_t, round(float(best_jump), 2)


def novelty_boundaries(x, sr=SR, seg_s=0.5, k=8):
    """Timbre-change peaks (candidate section boundaries), in seconds."""
    hop = int(sr * seg_s)
    feats = []
    for i in range(0, len(x) - hop, hop):
        m = np.abs(np.fft.rfft(x[i : i + hop] * np.hanning(hop), 4096))
        bands = [m[a:b].mean() for a, b in [(1, 8), (8, 24), (24, 64), (64, 160), (160, 400), (400, 1200), (1200, 2048)]]
        feats.append(np.log1p(np.array(bands) * 100))
    if len(feats) < 2 * k + 2:
        return []
    F = np.array(feats)
    F = (F - F.mean(0)) / (F.std(0) + 1e-6)
    nov = np.zeros(len(F))
    for i in range(k, len(F) - k):
        nov[i] = np.linalg.norm(F[i : i + k].mean(0) - F[i - k : i].mean(0))
    thr = np.percentile(nov, 80)
    peaks = []
    for i in range(1, len(nov) - 1):
        if nov[i] >= nov[i - 1] and nov[i] >= nov[i + 1] and nov[i] > thr and (not peaks or i - peaks[-1] > 6):
            peaks.append(i)
    return [round(p * seg_s, 2) for p in peaks]


# ----------------------------------------------------------------------------- tempo / beats


def tempo_autocorr(flux, fps, lo=70, hi=180):
    f = flux - np.convolve(flux, np.ones(16) / 16, "same")
    f = np.maximum(f, 0)
    ac = np.correlate(f, f, "full")[len(f) - 1 :]
    lags = np.arange(len(ac))
    with np.errstate(divide="ignore"):
        bpm = 60 * fps / lags
    mask = (bpm > lo) & (bpm < hi)
    if not mask.any():
        return 120.0
    return float(bpm[mask][np.argmax(ac[mask])])


def fold_bpm(bpm, hint):
    """Pick bpm, bpm/2 or bpm*2, whichever is nearest the requested tempo."""
    if not hint:
        return bpm
    return min((bpm / 2, bpm, bpm * 2, bpm * 2 / 3, bpm * 3 / 2), key=lambda b: abs(b - hint))


def beat_grid(flux, fps, dur, bpm_guess, span=2.0):
    """Fine-search period + phase that maximise the comb sum of onset strength."""
    f = (flux - flux.mean()) / (flux.std() + 1e-9)
    best = (-1e9, bpm_guess, 0.0)
    for bpm in np.arange(bpm_guess - span, bpm_guess + span, 0.02):
        period = 60.0 / bpm
        base = np.arange(0, dur, period)
        for ph in np.arange(0, period, 0.004):
            idx = np.round((ph + base) * fps).astype(int)
            idx = idx[idx < len(f)]
            s = f[idx].mean()
            if s > best[0]:
                best = (s, bpm, ph)
    _, bpm, ph = best
    period = 60.0 / bpm
    return float(bpm), ph + np.arange(0, dur - ph, period)


def downbeats_from_kick(beats, kick, fps, per_bar=4, anchor=None):
    """Which beat of the bar is "1". If an anchor is given (the drop, which almost always lands on
    a downbeat) it decides; otherwise the slot with the most kick energy wins. Kick-only voting
    is unreliable on breakbeats, so pass the drop whenever there is one."""
    if anchor is not None and len(beats):
        k0 = int(np.argmin(np.abs(beats - anchor))) % per_bar
        return beats[k0::per_bar], k0

    def strength(t):
        i = int(round(t * fps))
        return kick[max(0, i - 2) : i + 3].max() if i < len(kick) else 0

    slot = [sum(strength(b) for b in beats[k::per_bar]) for k in range(per_bar)]
    k0 = int(np.argmax(slot))
    return beats[k0::per_bar], k0


def tempo_drift(x, sr=SR):
    """|bpm(first half) - bpm(second half)|: a take that speeds up or wanders is hard to cut to."""
    half = len(x) // 2
    out = []
    for seg in (x[:half], x[half:]):
        mag, fps = stft_mag(seg)
        out.append(tempo_autocorr(band_flux(mag, 30, 11000), fps))
    a, b = out
    b = fold_bpm(b, a)
    return round(abs(a - b), 2), round(a, 1)


# ----------------------------------------------------------------------------- envelopes / hits


def rms_env(x, fps, sr=SR):
    hop = sr // fps
    e = np.array([np.sqrt(np.mean(x[i : i + hop] ** 2)) for i in range(0, len(x), hop)])
    return e / (e.max() + 1e-9)


def onset_env(sig, sig_fps, dur, fps):
    out = np.zeros(int(dur * fps) + 1)
    s = sig / (np.percentile(sig, 99) + 1e-9)
    for i, v in enumerate(s):
        j = int(i / sig_fps * fps)
        if j < len(out):
            out[j] = max(out[j], min(1.0, v))
    decay = 0.72 ** (30.0 / fps)  # a hit lingers ~120 ms at any fps
    for j in range(1, len(out)):
        out[j] = max(out[j], out[j - 1] * decay)
    return out


def drum_hits(x, end, sr=SR):
    """Strong kick / snare onsets (seconds) for SFX placement and visual punches."""
    n, hop = 1024, 128
    mag, fps = stft_mag(x, n, hop, sr)
    fr = np.fft.rfftfreq(n, 1 / sr)
    out = {}
    for name, lo, hi in [("kick", 30, 150), ("snare", 150, 4000)]:
        b = (fr >= lo) & (fr < hi)
        L = np.log1p(100 * mag[:, b])
        d = np.concatenate([[0], np.maximum(np.diff(L, axis=0), 0).sum(1)])
        t = (np.arange(len(d)) * hop + n / 2) / sr
        thr = np.percentile(d, 93)
        pk = [i for i in range(4, len(d) - 4) if d[i] == d[i - 4 : i + 5].max() and d[i] > thr]
        out[name] = [round(float(t[i]), 3) for i in pk if t[i] < end]
    return out


def vocal_onsets(path):
    """Onset times + strengths on a vocal stem (16 kHz analysis), plus the voiced phrases
    (runs of vocal energy separated by >= 0.2 s of silence) as [(start, end), ...]."""
    sr = 16000
    x = load(path, sr)
    n, hop = 512, 80
    mag, _ = stft_mag(x, n, hop, sr)
    fr = np.fft.rfftfreq(n, 1 / sr)
    b = (fr > 150) & (fr < 4000)
    L = np.log1p(50 * mag[:, b])
    flux = np.concatenate([[0], np.maximum(np.diff(L, axis=0), 0).sum(1)])
    rms = np.sqrt((mag[:, b] ** 2).mean(1))
    t = (np.arange(len(flux)) * hop + n / 2) / sr
    thr = np.percentile(flux, 80)
    pk = [
        i
        for i in range(3, len(flux) - 3)
        if flux[i] == flux[i - 3 : i + 4].max() and flux[i] > thr and rms[min(len(rms) - 1, i + 3)] > 0.08 * rms.max()
    ]
    voiced = np.convolve(rms, np.ones(5) / 5, "same") > 0.1 * rms.max()
    phrases, start, quiet = [], None, 0
    for i, v in enumerate(voiced):
        if v:
            if start is None:
                start = i
            quiet = 0
        elif start is not None:
            quiet += 1
            if quiet * hop / sr >= 0.2:
                end = i - quiet
                if (end - start) * hop / sr >= 0.15:
                    phrases.append((float(t[start]), float(t[end])))
                start, quiet = None, 0
    if start is not None:
        phrases.append((float(t[start]), float(t[-1])))
    return t[pk], flux[pk], phrases


# ----------------------------------------------------------------------------- lyrics


def norm_word(w):
    return re.sub(r"[^a-z0-9]", "", w.lower().replace("'", ""))


def parse_lyrics(text):
    """[section] tags + lines -> [{"section", "text", "words": [display words]}]. Tag-only lines and
    lines in parentheses (ad-libs / directions) are skipped."""
    lines, section = [], "verse"
    for raw in (text or "").splitlines():
        s = raw.strip()
        if not s:
            continue
        m = re.match(r"^\[([^\]]+)\]$", s)
        if m:
            section = re.split(r"\s+-\s+|:", m.group(1).strip())[0].strip().lower() or "verse"
            continue
        if s.startswith("(") and s.endswith(")"):
            continue
        words = [w for w in s.split() if norm_word(w)]
        if words and s.lower() != "[instrumental]":
            lines.append({"section": section, "text": s, "words": words})
    return lines


def load_transcript(path):
    data = json.load(open(path))
    if isinstance(data, dict):  # tolerate {"words": [...]} or parakeet-style {"sentences": [...]}
        if "words" in data:
            data = data["words"]
        else:  # parakeet-mlx: sub-word tokens; a leading space starts a new word
            words = []
            for sent in data.get("sentences", []):
                for i, t in enumerate(sent.get("tokens", [])):
                    if i == 0 or t["text"].startswith(" ") or not words:
                        words.append({"text": t["text"].strip(), "start": t["start"], "end": t.get("end", t["start"])})
                    else:
                        words[-1]["text"] += t["text"]
                        words[-1]["end"] = t.get("end", t["start"])
            data = words
    out = []
    for w in data:
        n = norm_word(w.get("text", ""))
        if n:
            out.append({"text": w["text"], "norm": n, "start": float(w["start"]), "end": float(w.get("end", w["start"]))})
    return out


def _sim(a, b):
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def align(sheet, heard, gap=-1.2, subst=-1.0):
    """Needleman-Wunsch over words, in order. Returns, per sheet word, (heard index | None, kind).
    Substitutions are allowed between matched neighbours, so a misheard word ("vibe" -> "eye",
    "render" -> "brenda") still gets the right time."""
    n, m = len(sheet), len(heard)
    S = np.zeros((n + 1, m + 1))
    B = np.zeros((n + 1, m + 1), dtype=np.int8)  # 0 diag, 1 up (sheet gap), 2 left (heard gap)
    S[1:, 0] = gap * np.arange(1, n + 1)
    S[0, 1:] = gap * np.arange(1, m + 1)
    B[1:, 0] = 1
    B[0, 1:] = 2
    score = np.zeros((n, m))
    for i, a in enumerate(sheet):
        for j, b in enumerate(heard):
            s = _sim(a, b["norm"])
            score[i, j] = 3.0 if s == 1.0 else 2.0 if s >= 0.75 else subst
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            opts = (S[i - 1, j - 1] + score[i - 1, j - 1], S[i - 1, j] + gap, S[i, j - 1] + gap)
            k = int(np.argmax(opts))
            S[i, j], B[i, j] = opts[k], k
    out = [(None, "missing")] * n
    i, j = n, m
    while i > 0 or j > 0:
        k = B[i, j]
        if i > 0 and j > 0 and k == 0:
            s = score[i - 1, j - 1]
            out[i - 1] = (j - 1, "exact" if s == 3.0 else "fuzzy" if s == 2.0 else "subst")
            i, j = i - 1, j - 1
        elif i > 0 and (j == 0 or k == 1):
            i -= 1
        else:
            j -= 1
    return out
