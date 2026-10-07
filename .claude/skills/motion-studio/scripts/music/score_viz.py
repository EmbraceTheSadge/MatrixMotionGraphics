"""Bake the REAL score into data the Composer world draws: waveform peaks + a pitch-tracked piano roll.

Usage: python3 score_viz.py <score.wav> <start_s> <end_s> <out.json> [bpm] [first_beat]
Times in the JSON are relative to start_s (the scene's local clock).
"""

import json
import subprocess
import sys

import numpy as np

SR = 22050
path, a, b, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
bpm = float(sys.argv[5]) if len(sys.argv) > 5 else 120.0
first_beat = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0

raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
x = np.frombuffer(raw, dtype=np.float32)
seg = x[int(a * SR) : int(b * SR)]
dur = len(seg) / SR

# --- waveform: 600 min/max bins
BINS = 600
step = max(1, len(seg) // BINS)
peaks = []
for i in range(BINS):
    s = seg[i * step : (i + 1) * step]
    if len(s) == 0:
        peaks.append([0, 0])
        continue
    peaks.append([round(float(s.min()), 3), round(float(s.max()), 3)])
pk = max(1e-6, max(max(abs(p[0]), abs(p[1])) for p in peaks))
peaks = [[round(p[0] / pk, 3), round(p[1] / pk, 3)] for p in peaks]

# --- piano roll: per 1/8-note frame, salient pitches 40..88 via harmonic-sum on a log-frequency spectrum
period = 60 / bpm
hop_t = period / 2
N = 8192
win = np.hanning(N)
freqs = np.fft.rfftfreq(N, 1 / SR)
midis = np.arange(40, 89)
mf = 440 * 2 ** ((midis - 69) / 12)
frames = []
t = (first_beat - a) % hop_t
while t < dur - 0.05:
    c = int(t * SR)
    s = seg[max(0, c - N // 2) : c + N // 2]
    if len(s) < N:
        s = np.pad(s, (0, N - len(s)))
    mag = np.abs(np.fft.rfft(s * win))
    sal = []
    for f in mf:
        v = 0
        for h, w in ((1, 1.0), (2, 0.5), (3, 0.33), (4, 0.25)):
            k = int(round(f * h / (SR / N)))
            if k < len(mag):
                v += w * mag[max(0, k - 1) : k + 2].max()
        sal.append(v)
    sal = np.array(sal)
    frames.append((round(t, 3), sal))
    t += hop_t

allsal = np.array([f[1] for f in frames])
thr = np.percentile(allsal, 84)
active = {}
notes = []
for t, sal in frames:
    order = np.argsort(sal)[::-1]
    chosen = []
    for i in order:
        if sal[i] < thr or len(chosen) >= 4:
            break
        if all(abs(i - j) not in (0, 12, 19, 24) for j in chosen):  # suppress octave/fifth harmonics
            chosen.append(i)
    now = set(int(midis[i]) for i in chosen)
    for m in list(active):
        if m not in now:
            st, vel = active.pop(m)
            notes.append({"t": st, "d": round(t - st, 3), "m": m, "v": vel})
    for i in chosen:
        m = int(midis[i])
        if m not in active:
            active[m] = (t, round(float(min(1, sal[i] / (thr * 3))), 2))
for m, (st, vel) in active.items():
    notes.append({"t": st, "d": round(dur - st, 3), "m": m, "v": vel})
notes.sort(key=lambda n: (n["t"], n["m"]))

beats = []
bt = first_beat
while bt < b:
    if bt >= a:
        beats.append(round(bt - a, 3))
    bt += period

json.dump({"source": path.split("/")[-1], "window": [a, b], "bpm": bpm, "beats": beats, "peaks": peaks, "notes": notes},
          open(out, "w"), separators=(",", ":"))
print(f"{out}: {len(notes)} notes, {len(peaks)} peaks, {len(beats)} beats, pitch range {min(n['m'] for n in notes)}-{max(n['m'] for n in notes)}")
