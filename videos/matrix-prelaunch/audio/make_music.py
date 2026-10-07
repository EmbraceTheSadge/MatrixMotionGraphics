"""Original minimal electronic rhythm for the Matrix prelaunch film — synthesized with numpy, seeded, $0.

    python audio/make_music.py [project_dir]   ->  assets/audio/music.wav (30.0 s, 48 kHz stereo)

Structure (120 BPM, beat = 0.5 s; times match STORYBOARD.md):
  0.0-3.0   sparse sub pulse every bar-half (1 s) + a soft tick           Portfolio
  3.0-6.0   pulse on every beat, closed hats on the off-beats            Market
  6.0-7.5   build: 16th hats crescendo, filtered-noise riser, kick roll   Connection
  7.5       drop-out -> the mark (impact lives in sfx.wav); low drone + pad
  9.5-19.5  groove: kick, off-beat bass, pluck arpeggio; claps from 13.0, open pluck from 16.5   Concept
  19.5-25.5 thinner groove (half-time kick, hats, bass)                  Live Archive
  25.5-30.0 resolve chord, one low pluck, decay to silence                End card
"""
import sys, os
import numpy as np

SR = 48000
DUR = 30.0
BPM = 120
BEAT = 60.0 / BPM
N = int(SR * DUR)
rng = np.random.default_rng(11)
L = np.zeros(N)
R = np.zeros(N)


def add(sig, t, gain=1.0, pan=0.0):
    i = int(round(t * SR))
    if i >= N:
        return
    sig = sig[: N - i] * gain
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    L[i:i + len(sig)] += sig * l * 1.414
    R[i:i + len(sig)] += sig * r * 1.414


def env(n, a=0.002, d=0.2, curve=4.0):
    t = np.arange(n) / SR
    att = np.clip(t / max(a, 1e-4), 0, 1)
    return att * np.exp(-curve * t / max(d, 1e-4))


def lp(x, cutoff):
    # one-pole low-pass (cutoff may be array)
    y = np.zeros_like(x)
    c = np.broadcast_to(cutoff, x.shape)
    a = 1 - np.exp(-2 * np.pi * c / SR)
    acc = 0.0
    for k in range(len(x)):
        acc += a[k] * (x[k] - acc)
        y[k] = acc
    return y


def hp(x, cutoff):
    return x - lp(x, cutoff)


def kick(level=1.0, dur=0.32):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 45 + 95 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * env(n, 0.001, dur * 0.55, 3.2)
    click = rng.standard_normal(n) * np.exp(-t * 400) * 0.15
    return (s + click) * level


def sub_pulse(freq=55, dur=0.6):
    n = int(SR * dur)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * freq * t) * env(n, 0.01, dur * 0.6, 3.0)


def hat(dur=0.045, open_=False):
    n = int(SR * (0.22 if open_ else dur))
    x = rng.standard_normal(n)
    x = hp(x, 7000)
    return x * env(n, 0.0005, (0.18 if open_ else dur), 4.0) * 0.35


def clap():
    n = int(SR * 0.18)
    x = hp(rng.standard_normal(n), 1200)
    e = np.zeros(n)
    for o in (0, 0.009, 0.018):
        i = int(o * SR)
        e[i:] += np.exp(-np.arange(n - i) / SR * 38)
    return x * e * 0.22


def pluck(freq, dur=0.35, bright=1.0):
    n = int(SR * dur)
    t = np.arange(n) / SR
    tri = 2 * np.abs(2 * ((freq * t) % 1) - 1) - 1
    sq = np.sign(np.sin(2 * np.pi * freq * t)) * 0.25 * bright
    return (tri + sq) * env(n, 0.002, dur * 0.5, 4.5) * 0.28


def bass(freq, dur=0.22):
    n = int(SR * dur)
    t = np.arange(n) / SR
    saw = 2 * ((freq * t) % 1) - 1
    s = 0.6 * np.sin(2 * np.pi * freq * t) + 0.4 * lp(saw, 420 + 1200 * np.exp(-t * 25))
    return s * env(n, 0.004, dur, 3.0) * 0.55


def pad(freqs, dur, a=0.4):
    n = int(SR * dur)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for k, f in enumerate(freqs):
        for det in (-0.12, 0.12):
            s += np.sin(2 * np.pi * (f + det) * t + k)
    s /= len(freqs) * 2
    shape = np.clip(t / a, 0, 1) * np.clip((dur - t) / (dur * 0.5), 0, 1)
    return lp(s, 1800) * shape * 0.22


def riser(dur):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    cut = 300 + 7000 * (t / dur) ** 2
    s = lp(x, cut) * (t / dur) ** 1.6
    tone = np.sin(2 * np.pi * np.cumsum(110 + 330 * (t / dur) ** 2) / SR) * (t / dur) ** 2 * 0.3
    return (s * 0.5 + tone) * 0.5


A1, C2, D2, E2, G1, F1 = 55.0, 65.41, 73.42, 82.41, 49.0, 43.65
PENTA = [220.0, 261.63, 293.66, 329.63, 392.0, 440.0, 523.25]  # A minor pentatonic
PROG = [A1, A1, F1, G1]  # one bar (2 s) each

# --- 0-3: sparse pulse
for t in np.arange(0, 3.0, 1.0):
    add(sub_pulse(55, 0.7), t, 0.55)
    add(kick(0.35, 0.25), t, 1.0)
for t in np.arange(0.5, 3.0, 1.0):
    add(hat(0.03), t, 0.35, 0.3)

# --- 3-6: every beat + off-beat hats
for t in np.arange(3.0, 6.0, BEAT):
    add(kick(0.55, 0.28), t)
    add(sub_pulse(55, 0.45), t, 0.35)
    add(hat(), t + BEAT / 2, 0.55, 0.25)
add(pad([110, 164.81, 220], 3.0, 1.2), 3.0, 0.6)

# --- 6-7.5: build
for k, t in enumerate(np.arange(6.0, 7.5, BEAT / 4)):
    add(hat(0.03), t, 0.25 + 0.6 * (t - 6.0) / 1.5, -0.3 if k % 2 else 0.3)
for t in np.arange(6.0, 7.0, BEAT):
    add(kick(0.6, 0.25), t)
for t in np.arange(7.0, 7.4, BEAT / 4):
    add(kick(0.45, 0.12), t)
add(riser(1.45), 6.0, 0.9)

# --- 7.5-9.5: after the mark, drone + pad (impact itself is in sfx.wav)
add(pad([55, 110, 164.81, 246.94, 329.63], 2.2, 0.05), 7.5, 1.0)
add(sub_pulse(55, 1.6), 7.5, 0.7)
for t in np.arange(8.5, 9.5, BEAT):
    add(kick(0.45, 0.25), t)
    add(hat(), t + BEAT / 2, 0.45, 0.2)

# --- 9.5-19.5: groove
t = 9.5
step = 0
while t < 19.5 - 1e-6:
    bar_i = int((t - 9.5) // 2.0)
    root = PROG[bar_i % 4]
    if step % 2 == 0:
        add(kick(0.75, 0.3), t)
    else:
        add(bass(root * 2, 0.22), t, 0.9)
        add(hat(), t, 0.55, 0.25)
    if t >= 13.0 and step % 4 == 2:
        add(clap(), t, 0.9, -0.1)
    # pluck arpeggio on 8ths, brighter after 16.5
    idx = [0, 2, 4, 3, 5, 3, 2, 4][step % 8]
    note = PENTA[idx] * (0.5 if root < 50 else 1.0)
    add(pluck(note, 0.3, bright=1.0 if t >= 16.5 else 0.4), t, 0.55 if t >= 16.5 else 0.42, 0.35 if step % 2 else -0.35)
    t += BEAT / 2
    step += 1

# --- 19.5-25.5: thinner groove
t = 19.5
step = 0
while t < 25.5 - 1e-6:
    if step % 4 == 0 and t >= 20.0:
        add(kick(0.6, 0.3), t)
    if step % 2 == 1:
        add(hat(), t, 0.45, 0.25)
        add(bass(A1 * 2 if int((t - 19.5) // 2) % 2 == 0 else F1 * 2, 0.2), t, 0.6)
    if step % 4 == 2:
        add(pluck(PENTA[[4, 5, 3, 2][int((t - 19.5) // 2) % 4]], 0.4, 0.5), t, 0.35)
    t += BEAT / 2
    step += 1

# --- 25.5-30: resolve
add(pad([110, 164.81, 220, 277.18, 329.63], 4.3, 0.25), 25.5, 1.1)
add(sub_pulse(55, 2.0), 25.5, 0.6)
add(pluck(110, 1.2, 0.3), 26.0, 0.6)
for t, g in ((26.5, 0.35), (27.5, 0.22), (28.5, 0.12)):
    add(kick(g, 0.3), t)

mix = np.stack([L, R], 1)
# gentle master: soft clip + normalize to -3 dBFS peak, fade the tail
mix = np.tanh(mix * 1.2) / np.tanh(1.2)
tail = int(SR * 0.6)
mix[-tail:] *= np.linspace(1, 0, tail)[:, None]
mix *= 10 ** (-3 / 20) / max(1e-9, np.abs(mix).max())

proj = sys.argv[1] if len(sys.argv) > 1 else "."
out = os.path.join(proj, "assets", "audio", "music.wav")
os.makedirs(os.path.dirname(out), exist_ok=True)
import wave
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print(f"music -> {out} ({DUR:.1f} s)")
