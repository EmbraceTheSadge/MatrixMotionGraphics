"""Matrix prelaunch film: original score + sound design, synthesized locally (numpy + scipy), seeded, $0.

    .claude/skills/motion-studio/scripts/py audio/score.py [project_dir]
      -> assets/audio/music.wav, assets/audio/sfx.wav (stems, already mastered together), audio/sound_cuesheet.md

Direction: warm, airy, optimistic "AI launch film" palette: felt piano, lush detuned pads, glassy FM bells,
sparkly delayed plucks, a soft modern pulse, swelling builds, and space. Key: D major (Lydian colour on the
reveals). Every effect is tuned to the key and generated with its own seed, so no two whooshes or plinks are
identical. Music and effects share one reverb space, the music ducks under the big moments, and both stems go
through one master limiter so they blend instead of stacking.

All times below are the film's timeline (see STORYBOARD.md / index.html).
"""
import os
import sys
import wave
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000
DUR = 40.4
N = int(SR * DUR)
BEAT = 0.5  # 120 BPM

# ---------------------------------------------------------------- buses
class Bus:
    def __init__(self):
        self.dry = np.zeros((N, 2))
        self.verb = np.zeros((N, 2))   # reverb send
        self.dly = np.zeros((N, 2))    # tempo delay send

MUS, SFX = Bus(), Bus()
CUES = []


def place(bus, sig, t, gain=1.0, pan=0.0, verb=0.25, dly=0.0):
    """Mix a mono or stereo signal into a bus at time t (seconds)."""
    i = int(round(t * SR))
    if i >= N or i + len(sig) <= 0:
        return
    if sig.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        sig = np.stack([sig * l, sig * r], 1) * 1.414
    if i < 0:
        sig = sig[-i:]
        i = 0
    sig = sig[: N - i] * gain
    bus.dry[i:i + len(sig)] += sig
    bus.verb[i:i + len(sig)] += sig * verb
    if dly:
        bus.dly[i:i + len(sig)] += sig * dly


def cue(t, what):
    CUES.append((t, what))


# ---------------------------------------------------------------- helpers
def tt(d):
    return np.arange(int(d * SR)) / SR


def lp(x, f, order=2):
    return sosfilt(butter(order, min(f, SR * 0.45), "low", fs=SR, output="sos"), x, axis=0)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x, axis=0)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, min(hi, SR * 0.45)], "band", fs=SR, output="sos"), x, axis=0)


def adsr(n, a=0.005, d=0.1, s=0.7, r=0.2):
    e = np.ones(n) * s
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    na = max(1, min(na, n)); e[:na] = np.linspace(0, 1, na)
    nd = min(nd, n - na)
    if nd > 0:
        e[na:na + nd] = np.linspace(1, s, nd)
    if nr > 0 and nr < n:
        e[-nr:] *= np.linspace(1, 0, nr) ** 1.5
    return e


def fade(x, fin=0.002, fout=0.02):
    a, b = int(fin * SR), int(fout * SR)
    if a: x[:a] *= np.linspace(0, 1, a)[:, None] if x.ndim == 2 else np.linspace(0, 1, a)
    if b: x[-b:] *= np.linspace(1, 0, b)[:, None] if x.ndim == 2 else np.linspace(1, 0, b)
    return x


def note(name):
    names = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[n] + (o - 4) * 12) / 12)


def chord(names):
    return [note(n) for n in names.split()]


# ---------------------------------------------------------------- instruments
def felt_piano(f, dur=2.5, vel=1.0, seed=0):
    r = np.random.default_rng(seed)
    t = tt(dur)
    out = np.zeros(len(t))
    B = 0.00035
    for k in range(1, 13):
        fk = k * f * np.sqrt(1 + B * k * k)
        if fk > 9000:
            break
        amp = vel * (1 / k ** 1.15) * np.exp(-fk / 2600)
        dec = 0.55 + 0.32 * k + f / 900
        for det in (-0.0006, 0.0006):
            out += amp * 0.5 * np.sin(2 * np.pi * fk * (1 + det) * t + r.uniform(0, 6.28)) * np.exp(-dec * t)
    ham = lp(hp(r.standard_normal(int(0.02 * SR)), 900), 3200) * np.exp(-np.arange(int(0.02 * SR)) / SR * 220) * 0.05 * vel
    out[:len(ham)] += ham
    out *= np.minimum(1, t / 0.004)
    return fade(lp(out, 5200), 0.0, 0.08)


def pad(freqs, dur, att=1.2, rel=1.4, bright=1800, seed=1, voices=3):
    r = np.random.default_rng(seed)
    t = tt(dur)
    sig = np.zeros(len(t))
    for f in freqs:
        for v in range(voices):
            det = 1 + (v - (voices - 1) / 2) * 0.0045
            ph = r.uniform(0, 6.28, 16)
            for k in range(1, 15):
                if k * f > 7000:
                    break
                sig += np.sin(2 * np.pi * k * f * det * t + ph[k]) / k
    sig /= max(1, len(freqs) * voices) * 2.2
    lfo = 1 + 0.25 * np.sin(2 * np.pi * 0.18 * t + r.uniform(0, 6.28))
    # slowly opening low-pass: render in 3 bands and crossfade for a moving filter
    a, b = lp(sig, bright * 0.5), lp(sig, bright * 1.6)
    mix = a + (b - a) * np.clip(t / max(dur * 0.6, 0.1), 0, 1)[:] * 0.8
    env = np.minimum(1, t / att) * np.clip((dur - t) / rel, 0, 1) * lfo
    return mix * env


def pluck(f, dur=0.45, vel=1.0, tone=2400, seed=2):
    t = tt(dur)
    s = np.zeros(len(t))
    for k in range(1, 10):
        if k * f > 9000:
            break
        s += np.sin(2 * np.pi * k * f * t) / k * (1.0 if k % 2 else 0.55)
    env = np.exp(-t * 9) * np.minimum(1, t / 0.002)
    return fade(lp(s * env * vel * 0.4, tone), 0, 0.03)


def bell(f, dur=2.2, vel=1.0, ratio=3.5, idx=2.2, seed=3):
    t = tt(dur)
    mod = idx * np.exp(-t * 3.2) * np.sin(2 * np.pi * f * ratio * t)
    s = np.sin(2 * np.pi * f * t + mod) * np.exp(-t * 2.2) * np.minimum(1, t / 0.002)
    s += 0.25 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t * 4)
    return fade(s * vel * 0.35, 0, 0.05)


def glass(f, dur=0.9, vel=1.0, seed=4):
    r = np.random.default_rng(seed)
    t = tt(dur)
    ratio = r.choice([2.76, 3.0, 4.07, 5.4])
    mod = (1.4 + r.uniform(0, 0.8)) * np.exp(-t * 18) * np.sin(2 * np.pi * f * ratio * t)
    s = np.sin(2 * np.pi * f * t + mod) * np.exp(-t * (5 + r.uniform(0, 3))) * np.minimum(1, t / 0.0015)
    return fade(s * vel * 0.3, 0, 0.03)


def sub(f, dur, vel=1.0, glide=0.0):
    t = tt(dur)
    ff = f * (1 + glide * np.exp(-t * 18))
    s = np.tanh(1.6 * np.sin(2 * np.pi * np.cumsum(ff) / SR)) * 0.7
    return s * adsr(len(t), 0.01, 0.2, 0.75, min(0.4, dur * 0.5)) * vel


def kick(vel=1.0, seed=5):
    r = np.random.default_rng(seed)
    t = tt(0.42)
    f = 46 + 70 * np.exp(-t * 32)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.5)
    s += lp(r.standard_normal(len(t)), 2500) * np.exp(-t * 160) * 0.12
    return np.tanh(1.3 * s) * vel * 0.8


def clap(vel=1.0, seed=6):
    r = np.random.default_rng(seed)
    t = tt(0.35)
    n = bp(r.standard_normal(len(t)), 900, 5200)
    e = np.zeros(len(t))
    for o in (0, 0.008, 0.017, 0.026):
        i = int(o * SR); e[i:] += np.exp(-(np.arange(len(t) - i)) / SR * (60 if o < 0.02 else 18))
    return n * e * vel * 0.22


def snap(vel=1.0, seed=7):
    r = np.random.default_rng(seed)
    t = tt(0.12)
    return bp(r.standard_normal(len(t)), 1800, 7000) * np.exp(-t * 70) * vel * 0.3


def shaker(vel=1.0, seed=8):
    r = np.random.default_rng(seed)
    t = tt(0.09)
    e = np.minimum(1, t / 0.012) * np.exp(-t * 45)
    return hp(r.standard_normal(len(t)), 5500) * e * vel * 0.14


def riser(dur, f0=300, f1=6000, seed=9):
    r = np.random.default_rng(seed)
    t = tt(dur)
    x = r.standard_normal(len(t))
    u = t / dur
    out = np.zeros(len(t))
    # moving band-pass, in 12 overlapping segments
    seg = 12
    for k in range(seg):
        c = f0 * (f1 / f0) ** ((k + 0.5) / seg)
        w = np.clip(1 - np.abs(u * seg - k - 0.5), 0, 1)
        out += bp(x, c * 0.7, c * 1.4) * w
    return out * u ** 1.8 * 0.5


def reverse_swell(sig):
    return sig[::-1].copy()


# ---------------------------------------------------------------- sound-design families (each call is unique)
def whoosh(dur=0.7, seed=0, lo=None, hi=None):
    r = np.random.default_rng(seed)
    t = tt(dur)
    lo = lo or r.uniform(180, 420)
    hi = hi or r.uniform(2400, 5200)
    x = r.standard_normal(len(t))
    u = t / dur
    peak = r.uniform(0.5, 0.65)
    env = np.where(u < peak, (u / peak) ** 2.2, ((1 - u) / (1 - peak)) ** 1.6)
    out = np.zeros(len(t))
    for k in range(8):
        c = lo * (hi / lo) ** (np.sin(np.pi * min(1, (k + 0.5) / 8)) * 0.85 + 0.15 * (k / 8))
        w = np.clip(1 - np.abs(u * 8 - k - 0.5), 0, 1)
        out += bp(x, c * 0.6, c * 1.6) * w
    return out * env * 0.32


def stereo_sweep(m, p0, p1):
    n = len(m)
    p = np.linspace(p0, p1, n)
    return np.stack([m * np.cos((p + 1) * np.pi / 4), m * np.sin((p + 1) * np.pi / 4)], 1) * 1.414


def ui_click(seed=0, pitch=None):
    r = np.random.default_rng(seed)
    t = tt(0.06)
    f = pitch or r.uniform(1800, 2600)
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 140) * 0.35
    s += bp(r.standard_normal(len(t)), 2500, 9000) * np.exp(-t * 260) * 0.25
    return s


def soft_pop(f, seed=0):
    t = tt(0.25)
    ff = f * (1 + 0.6 * np.exp(-t * 40))
    return np.sin(2 * np.pi * np.cumsum(ff) / SR) * np.exp(-t * 16) * np.minimum(1, t / 0.002) * 0.45


def boom(dur=2.2, f=44):
    t = tt(dur)
    ff = f * (1 + 1.2 * np.exp(-t * 9))
    s = np.sin(2 * np.pi * np.cumsum(ff) / SR) * np.exp(-t * 1.6)
    return np.tanh(1.4 * s) * 0.9


def air_impact(seed=0):
    r = np.random.default_rng(seed)
    t = tt(1.6)
    n = lp(r.standard_normal(len(t)), 1400) * np.exp(-t * 5) * 0.35
    return n


def shimmer(dur=1.4, base=note("D6"), seed=0, up=True):
    r = np.random.default_rng(seed)
    out = np.zeros(int(dur * SR))
    scale = [0, 2, 4, 7, 9, 12, 14, 16, 19]
    for k in range(18):
        st = (k / 18) * dur * 0.75 + r.uniform(0, 0.05)
        deg = scale[min(len(scale) - 1, int((k / 18 if up else 1 - k / 18) * len(scale)))]
        g = glass(base * 2 ** (deg / 12), 0.5, 0.35 + 0.3 * r.random(), seed=seed * 31 + k)
        i = int(st * SR)
        out[i:i + len(g)] += g[: len(out) - i]
    return out * np.minimum(1, np.arange(len(out)) / SR / 0.2)


# ================================================================= SCORE
D = {k: chord(v) for k, v in {
    "Dmaj9": "D3 A3 E4 F#4 C#5", "Bm9": "B2 F#3 A3 C#4 D4", "Gmaj7#11": "G2 D3 F#3 B3 C#4",
    "Asus": "A2 E3 B3 D4 E4", "D/F#": "F#2 D3 A3 E4", "Em9": "E2 B2 D3 F#3 G3", "Dhigh": "D4 F#4 A4 C#5 E5"}.items()}
ROOT = {"Dmaj9": note("D2"), "Bm9": note("B1"), "Gmaj7#11": note("G1"), "Asus": note("A1"), "D/F#": note("F#2"), "Em9": note("E2")}


def piano_chord(t, name, vel=0.8, spread=0.018, dur=3.0, seed=0, verb=0.4, gain=1.0):
    for k, f in enumerate(D[name]):
        place(MUS, felt_piano(f, dur, vel * (0.85 if k else 1.0), seed=seed + k), t + k * spread, gain * 0.5, pan=-0.25 + 0.5 * k / max(1, len(D[name]) - 1), verb=verb)


def pad_at(t, name, dur, gain=0.5, att=1.2, rel=1.4, bright=1800, seed=1, verb=0.55):
    place(MUS, pad(D[name], dur, att, rel, bright, seed), t, gain, verb=verb)


def bass_at(t, name, dur, vel=0.7):
    place(MUS, sub(ROOT[name], dur, vel), t, 0.55, verb=0.0)


def arp(t0, t1, names, step=0.125, vel=0.5, tone=2600, pattern=(0, 2, 1, 3, 2, 4, 3, 1), seed=11, octave=2.0, pan_w=0.5, descend=False):
    k = 0
    t = t0
    while t < t1 - 1e-6:
        bar = names[int((t - t0) // 2.0) % len(names)]
        fs = sorted(D[bar])
        idx = pattern[k % len(pattern)]
        if descend:
            idx = len(fs) - 1 - (k % len(fs))
        f = fs[idx % len(fs)] * octave
        v = vel * (0.75 + 0.25 * ((k % 4) == 0))
        place(MUS, pluck(f, 0.4, v, tone, seed + k), t, 0.42, pan=pan_w * (1 if k % 2 else -1), verb=0.3, dly=0.35)
        t += step
        k += 1


def drums(t0, t1, kick_every=1.0, clap_on=False, shaker_on=True, vel=1.0, seed=100, snap_on=False):
    k = 0
    t = t0
    while t < t1 - 1e-6:
        beat = round((t - t0) / BEAT)
        if (t - t0) % kick_every < 1e-6 or abs(((t - t0) % kick_every) - kick_every) < 1e-6:
            place(MUS, kick(vel, seed + k), t, 0.7, verb=0.02)
        if clap_on and beat % 2 == 1:
            place(MUS, clap(vel * 0.8, seed + 3 * k), t, 0.55, pan=0.05, verb=0.35)
        if snap_on and beat % 2 == 1:
            place(MUS, snap(vel * 0.8, seed + 5 * k), t, 0.5, pan=-0.1, verb=0.3)
        if shaker_on:
            for s in range(2):
                ts = t + s * 0.25 + (0.018 if s else 0)
                place(MUS, shaker(vel * (0.6 if s == 0 else 1.0), seed + 7 * k + s), ts, 0.5, pan=0.35, verb=0.15)
        t += BEAT
        k += 1


# --- 0-6: the portfolio pieces, one at a time (felt piano, air pad, glass)
place(MUS, reverse_swell(felt_piano(note("D4"), 1.0, 0.7, seed=1)), 0.0, 0.35, verb=0.5)
pad_at(0.4, "Dmaj9", 6.2, gain=0.32, att=2.2, bright=1200, seed=2)
tab_notes = [("D4", "A4"), ("F#4", "C#5"), ("A4", "E5"), ("B4", "F#5")]
for k, (a, b) in enumerate(tab_notes):
    t = 1.0 + k
    place(MUS, felt_piano(note(a), 2.4, 0.75, seed=10 + k), t, 0.5, pan=-0.2, verb=0.45)
    place(MUS, felt_piano(note(b), 2.4, 0.6, seed=20 + k), t + 0.03, 0.42, pan=0.2, verb=0.45)
bass_at(1.0, "Dmaj9", 4.0, 0.35)
piano_chord(5.0, "Dhigh", 0.7, spread=0.035, dur=3.2, seed=40)
place(MUS, bell(note("A5"), 2.5, 0.6), 5.8, 0.4, pan=0.3, verb=0.6, dly=0.3)

# --- 6-9.5: zoom out; the market arrives (pulse begins, Bm colour, plucks open up)
pad_at(6.0, "Bm9", 2.2, gain=0.36, att=0.6, bright=1500, seed=3)
pad_at(8.0, "Gmaj7#11", 1.7, gain=0.36, att=0.4, bright=1800, seed=4)
bass_at(6.0, "Bm9", 2.0, 0.5); bass_at(8.0, "Gmaj7#11", 1.5, 0.5)
drums(6.0, 9.5, kick_every=1.0, shaker_on=True, vel=0.7, seed=200)
arp(6.5, 9.5, ["Bm9", "Gmaj7#11"], step=0.25, vel=0.42, tone=1800, seed=300)
piano_chord(8.0, "Bm9", 0.55, spread=0.03, dur=2.5, seed=50)
place(MUS, bell(note("F#5"), 2.0, 0.45), 8.45, 0.35, pan=0.45, verb=0.6, dly=0.3)

# --- 9.5-11: build into the merge (Asus lift, 16th plucks, clap roll, riser), short breath before the hit
pad_at(9.5, "Asus", 1.45, gain=0.42, att=0.3, bright=3200, seed=5)
bass_at(9.5, "Asus", 1.35, 0.55)
arp(9.5, 10.85, ["Asus"], step=0.125, vel=0.45, tone=3400, seed=400)
for k, t in enumerate(np.arange(9.5, 10.9, 0.125)):
    v = 0.25 + 0.75 * ((t - 9.5) / 1.4) ** 2
    place(MUS, clap(v * 0.6, 500 + k), t, 0.35, pan=0.1 * (1 if k % 2 else -1), verb=0.3)
place(MUS, riser(1.5, 250, 7000, seed=6), 9.4, 0.55, verb=0.4)

# --- 11: NOW TOGETHER: the bloom (big Lydian chord, sub, bell motif), then float
pad_at(11.0, "Dmaj9", 3.0, gain=0.55, att=0.02, rel=2.0, bright=3200, seed=7, verb=0.7)
piano_chord(11.0, "Dmaj9", 0.95, spread=0.012, dur=4.0, seed=60, verb=0.55)
bass_at(11.0, "Dmaj9", 2.4, 0.8)
for k, (n, dt) in enumerate([("A5", 0.45), ("F#5", 0.7), ("D6", 0.95), ("E6", 1.45)]):
    place(MUS, bell(note(n), 2.4, 0.55), 11.0 + dt, 0.36, pan=-0.3 + 0.2 * k, verb=0.65, dly=0.35)
pad_at(12.6, "Dmaj9", 1.6, gain=0.3, att=0.5, bright=1600, seed=8)
for t in np.arange(12.5, 13.5, BEAT):
    place(MUS, kick(0.45, 600 + int(t * 10)), t, 0.6, verb=0.02)

# --- 13.5-18.5: markets, minus the bottleneck (half-time pulse, minor colour, falling piano with the chart)
pad_at(13.5, "Bm9", 3.0, gain=0.38, att=0.6, bright=1300, seed=9)
pad_at(16.4, "Em9", 2.2, gain=0.36, att=0.5, bright=1400, seed=10)
bass_at(13.5, "Bm9", 2.9, 0.55); bass_at(16.4, "Em9", 2.1, 0.5)
drums(13.5, 18.5, kick_every=1.0, shaker_on=True, vel=0.6, seed=700, snap_on=True)
for k, n in enumerate(["F#5", "E5", "D5", "C#5", "B4", "A4", "F#4"]):        # follows the downtrend
    place(MUS, felt_piano(note(n), 1.6, 0.62 - 0.03 * k, seed=70 + k), 14.6 + k * 0.28, 0.42, pan=0.25 - 0.08 * k, verb=0.5, dly=0.25)
piano_chord(17.15, "Gmaj7#11", 0.7, spread=0.025, dur=2.6, seed=80)        # the plain-language line lands, warm

# --- 18.5-21.5: know your next move (lift to A, then home; plucks return)
pad_at(18.5, "Asus", 1.6, gain=0.4, att=0.4, bright=2200, seed=11)
pad_at(19.3, "Dmaj9", 2.4, gain=0.42, att=0.2, bright=2600, seed=12)
bass_at(18.5, "Asus", 0.8, 0.55); bass_at(19.3, "Dmaj9", 2.2, 0.6)
drums(18.5, 21.5, kick_every=1.0, shaker_on=True, vel=0.7, seed=900, snap_on=True)
arp(19.3, 21.5, ["Dmaj9"], step=0.25, vel=0.4, tone=2600, seed=1000)
piano_chord(19.3, "Dhigh", 0.75, spread=0.02, dur=2.4, seed=90)

# --- 21.5-29.7: and exactly why (the fullest groove; plucks descend with the price; resolves on the summary)
prog = ["Dmaj9", "Bm9", "Gmaj7#11", "Asus"]
for k, t in enumerate(np.arange(21.5, 29.5, 2.0)):
    name = prog[k % 4]
    pad_at(t, name, 2.1, gain=0.38, att=0.15, rel=0.6, bright=2400, seed=20 + k)
    bass_at(t, name, 1.95, 0.62)
drums(21.5, 29.5, kick_every=0.5, clap_on=True, shaker_on=True, vel=0.75, seed=1200)
arp(21.5, 24.0, prog, step=0.125, vel=0.38, tone=2800, seed=1300)
arp(24.0, 27.6, prog, step=0.125, vel=0.42, tone=2400, seed=1400, descend=True)
arp(27.6, 29.5, prog, step=0.125, vel=0.44, tone=3600, seed=1500)
piano_chord(27.85, "Dhigh", 0.8, spread=0.15, dur=2.0, seed=100)            # three summary chips = one rising chord
place(MUS, riser(0.6, 400, 5000, seed=7), 29.15, 0.35, verb=0.4)

# --- 29.7-36: the live Archive (airier, half-time, piano chords)
for k, (t, name) in enumerate([(29.7, "Dmaj9"), (31.7, "Gmaj7#11"), (33.7, "Bm9"), (35.0, "Asus")]):
    pad_at(t, name, 2.2 if k < 3 else 1.1, gain=0.34, att=0.3, bright=2000, seed=40 + k)
    bass_at(t, name, 1.9 if k < 3 else 1.0, 0.5)
    piano_chord(t + 0.02, name, 0.55, spread=0.04, dur=2.0, seed=110 + 10 * k)
drums(30.0, 35.5, kick_every=1.0, shaker_on=True, vel=0.55, seed=1600)
arp(33.7, 35.9, ["Bm9", "Asus"], step=0.25, vel=0.32, tone=2200, seed=1700)
place(MUS, riser(0.9, 300, 6500, seed=8), 35.15, 0.4, verb=0.4)

# --- 36-40.4: the end card (final bloom, bell sting, long tail)
pad_at(36.25, "Dmaj9", 4.1, gain=0.52, att=0.05, rel=2.4, bright=3000, seed=60, verb=0.75)
piano_chord(36.25, "Dmaj9", 0.9, spread=0.015, dur=4.0, seed=130, verb=0.6)
bass_at(36.25, "Dmaj9", 3.6, 0.75)
for k, (n, dt) in enumerate([("D6", 0.0), ("A5", 0.35), ("F#6", 0.75)]):
    place(MUS, bell(note(n), 3.0, 0.55), 36.6 + dt, 0.36, pan=-0.2 + 0.2 * k, verb=0.7, dly=0.35)
place(MUS, felt_piano(note("D3"), 3.4, 0.6, seed=150), 38.0, 0.45, verb=0.6)

# ================================================================= SOUND DESIGN (tuned, varied, placed on the picture)
def W(t_peak, dur, gain, p0, p1, seed, verb=0.3, lo=None, hi=None, label=""):
    m = whoosh(dur, seed, lo, hi)
    place(SFX, stereo_sweep(m, p0, p1), t_peak - dur * 0.57, gain, verb=verb)
    cue(t_peak, "whoosh · " + label)


def G(t, f, gain, pan, seed, label="", verb=0.45, dly=0.25):
    place(SFX, glass(f, 0.9, 1.0, seed), t, gain, pan=pan, verb=verb, dly=dly)
    cue(t, "glass " + label)


# intro: each tab opens with a tuned glass tick, then glides into the orbit with a soft, unique whoosh
tab_tones = ["A5", "C#6", "E6", "F#6"]
for k in range(4):
    t0 = 1.0 + k
    G(t0 + 0.02, note(tab_tones[k]), 0.5, -0.15 + 0.1 * k, 50 + k, f"tab {k + 1} opens")
    place(SFX, ui_click(60 + k), t0, 0.35, pan=0.0, verb=0.2)
    W(t0 + 0.85, 0.55, 0.42, 0.0, [-0.6, 0.6, -0.5, 0.5][k], 70 + k, label=f"tab {k + 1} joins the orbit")
G(5.32, note("D6"), 0.32, 0.0, 80, "Your portfolio.")
place(SFX, shimmer(1.1, note("D6"), 81), 5.8, 0.28, pan=-0.1, verb=0.5); cue(5.8, "shimmer · Everywhere.")
W(6.45, 1.0, 0.5, 0.3, -0.7, 90, verb=0.4, lo=150, hi=2200, label="zoom out")
W(7.25, 0.7, 0.55, 0.9, 0.35, 91, label="charts tab swings in")
W(7.75, 0.7, 0.5, 0.9, 0.45, 92, label="news tab swings in")
G(8.0, note("B5"), 0.3, 0.4, 93, "The market.")
place(SFX, shimmer(1.0, note("F#6"), 94, up=False), 8.45, 0.24, pan=0.4, verb=0.5); cue(8.45, "shimmer · Elsewhere.")
# merge
W(9.95, 0.9, 0.62, -0.4, 0.4, 100, verb=0.35, label="tabs fly into the mosaic")
for k, t in enumerate([9.62, 9.73, 9.86, 9.97, 10.06, 10.18]):
    place(SFX, ui_click(110 + k, pitch=1400 + 180 * k), t + 0.6, 0.3, pan=-0.5 + 0.2 * k, verb=0.2)
cue(10.3, "six tiles lock (6 tuned clicks)")
place(SFX, ui_click(120, pitch=900), 10.9, 0.5, verb=0.3); cue(10.9, "gaps close")
# the X lands
place(SFX, boom(2.4), 11.0, 0.95, verb=0.25)
place(SFX, air_impact(130), 11.0, 0.7, verb=0.6)
for k, n in enumerate(["D5", "A5", "E6"]):
    place(SFX, bell(note(n), 2.6, 0.7), 11.0, 0.35, pan=-0.3 + 0.3 * k, verb=0.7)
cue(11.0, "IMPACT · the Matrix X (sub boom + air + Lydian bell chord)")
place(SFX, shimmer(1.2, note("A5"), 131), 11.15, 0.3, pan=0.3, verb=0.55); cue(11.15, "scan sweep shimmer")
G(11.45, note("F#6"), 0.25, 0.0, 132, "Now together.")

# middle
W(13.85, 0.9, 0.5, -0.4, 0.4, 140, verb=0.4, label="rectangle opens into the window")
place(SFX, ui_click(141, pitch=2100), 14.3, 0.3, verb=0.3); cue(14.3, "logo settles in the header")
place(SFX, stereo_sweep(lp(whoosh(1.8, 142, 160, 1400), 1500), -0.5, 0.5), 14.6, 0.32, verb=0.45); cue(15.5, "downtrend draws (dark air)")
G(16.4, note("D5"), 0.22, 0.3, 143, "trendline")
place(SFX, stereo_sweep(whoosh(0.6, 144, 300, 2600)[::-1].copy(), 0.4, 0.0), 16.75, 0.35, verb=0.4); cue(17.1, "chart folds (reverse air)")
place(SFX, soft_pop(note("G4")), 17.15, 0.4, verb=0.4); G(17.17, note("B5"), 0.3, 0.0, 145, "Bear market · Downtrend lands")
W(18.82, 0.6, 0.36, -0.2, -0.6, 146, label="badge tucks to the top row")
place(SFX, soft_pop(note("A4")), 19.3, 0.38, verb=0.4); G(19.32, note("A5"), 0.32, 0.0, 147, "Asset accumulation card")
for k, n in enumerate(["D6", "F#6", "A6"]):
    G(19.75 + 0.12 * k, note(n), 0.2, -0.3 + 0.3 * k, 148 + k, f"chip {k + 1}")
W(21.85, 0.8, 0.5, 0.2, -0.3, 150, verb=0.35, label="card opens into the LP explainer")
G(22.45, note("D6"), 0.25, 0.0, 151, "price at the top of the range")
place(SFX, soft_pop(note("D5")), 22.75, 0.3, pan=0.5, verb=0.3); cue(22.75, "Deposit · 4,000 USDC")
for k, n in enumerate(["D6", "C#6", "B5", "A5", "G5", "F#5", "E5", "D5"]):     # coins drop into the range: a falling scale
    t = 22.95 + k * 0.1 + 0.7
    place(SFX, glass(note(n), 0.5, 0.7, 160 + k), t, 0.24, pan=-0.35 + 0.08 * k, verb=0.35, dly=0.15)
    place(SFX, ui_click(170 + k, pitch=900 + 60 * k), t, 0.15, pan=-0.35 + 0.08 * k, verb=0.1)
cue(23.65, "8 USDC coins land (falling D-major scale)")
place(SFX, stereo_sweep(lp(whoosh(3.6, 180, 140, 1100), 1200), 0.4, -0.3), 24.0, 0.2, verb=0.5); cue(24.0, "descent bed (low air)")
fee_t = [24.2, 24.387, 24.574, 24.761, 24.948, 25.135, 25.322, 25.509, 25.696, 25.883]
fee_n = ["D6", "E6", "F#6", "A6", "B6", "D7", "B6", "D7", "E7", "F#7"]           # fees climb while the price falls
for k, (ts, n) in enumerate(zip(fee_t, fee_n)):
    G(ts + 0.7, note(n), 0.22, 0.55 - 0.05 * k, 190 + k, f"fee coin {k + 1}", dly=0.3)
place(SFX, felt_piano(note("D3"), 1.6, 0.6, seed=200), 26.25, 0.35, verb=0.4); cue(26.25, "below range · fees paused (low D)")
for k, n in enumerate(["D5", "F#5", "A5"]):
    place(SFX, soft_pop(note(n)), 27.85 + 0.15 * k, 0.32, pan=-0.3 + 0.3 * k, verb=0.35)
cue(27.85, "summary chips (D-F#-A)")

# archive
W(29.82, 0.9, 0.55, 0.3, -0.3, 210, verb=0.4, label="window becomes the live Archive")
for k, (t, label) in enumerate([(30.7, "ENTER THE ARCHIVE"), (31.8, "Bear"), (32.9, "OPEN RECORD")]):
    place(SFX, ui_click(220 + k, pitch=[2300, 2000, 2500][k]), t, 0.55, pan=-0.1 + 0.1 * k, verb=0.2)
    place(SFX, soft_pop(note(["A4", "F#4", "D5"][k])), t + 0.01, 0.18, verb=0.3)
    place(SFX, stereo_sweep(whoosh(0.35, 230 + k, 900, 5000), 0.2, -0.2), t - 0.45, 0.14, verb=0.15)
    cue(t, "click · " + label)
W(33.9, 0.8, 0.45, -0.2, 0.3, 240, label="zoom into the Overview")
place(SFX, shimmer(1.0, note("D6"), 241), 34.6, 0.22, pan=-0.2, verb=0.5); cue(34.6, "highlight sweep")
# end
W(36.1, 0.7, 0.55, 0.4, 0.0, 250, label="window collapses into the mark")
place(SFX, boom(1.6, 50), 36.25, 0.55, verb=0.3); cue(36.25, "mark lands (soft sub)")
place(SFX, soft_pop(note("D5")), 36.6, 0.3, verb=0.4); G(36.62, note("A6"), 0.3, 0.1, 251, "Join the waitlist")
G(36.75, note("D6"), 0.2, -0.1, 252, "matrix.finance")

# ================================================================= MIX
def reverb_ir(rt60=2.4, seed=3):
    r = np.random.default_rng(seed)
    n = int(rt60 * SR)
    t = np.arange(n) / SR
    env = np.exp(-6.9 * t / rt60)
    ir = np.stack([r.standard_normal(n), r.standard_normal(n)], 1) * env[:, None]
    ir = lp(ir, 5200)
    ir[:int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))[:, None]
    for d, g in ((0.011, 0.5), (0.017, 0.35), (0.023, 0.28), (0.031, 0.2)):
        ir[int(d * SR), 0] += g; ir[int((d + 0.003) * SR), 1] += g
    return ir / np.sqrt((ir ** 2).sum(0, keepdims=True))


def apply_verb(x, ir):
    y = np.stack([fftconvolve(x[:, c], ir[:, c])[:N] for c in range(2)], 1)
    return hp(y, 180)


def apply_delay(x, t=0.375, fb=0.38):
    y = np.zeros_like(x)
    d = int(t * SR)
    buf = x.copy()
    g = 1.0
    for k in range(6):
        g *= fb
        sh = d * (k + 1)
        if sh >= N:
            break
        # ping-pong: alternate channels
        src = buf[: N - sh]
        if k % 2 == 0:
            y[sh:, 0] += src[:, 1] * g; y[sh:, 1] += src[:, 0] * g
        else:
            y[sh:] += src * g
    return lp(hp(y, 400), 6000)


IR = reverb_ir()
music = MUS.dry + apply_verb(MUS.verb, IR) * 0.85 + apply_delay(MUS.dly) * 0.6
sfx = SFX.dry + apply_verb(SFX.verb, IR) * 0.85 + apply_delay(SFX.dly) * 0.5
music = hp(music, 28)
sfx = hp(sfx, 45)

# duck the music under the big moments so the effects sit inside it
duck = np.ones(N)
for t, depth, rel in ((11.0, 0.45, 0.9), (29.75, 0.7, 0.6), (36.1, 0.6, 0.7), (13.85, 0.8, 0.5), (21.85, 0.8, 0.5)):
    i = int(t * SR); a = int(0.03 * SR); n = int(rel * SR)
    seg = np.concatenate([np.linspace(1, depth, a), depth + (1 - depth) * (1 - np.exp(-np.arange(n) / SR * 5.0 / rel))])
    j = min(N, i - a + len(seg))
    duck[i - a:j] = np.minimum(duck[i - a:j], seg[: j - (i - a)])
music *= duck[:, None]

# gentle glue on the music (slow RMS compressor), then fade the ends
env = np.sqrt(lp(np.mean(music ** 2, 1), 6, order=1).clip(1e-9))
thr = np.percentile(env, 92) * 0.8
gain = np.where(env > thr, (thr / env) ** 0.35, 1.0)
music *= gain[:, None]
for x in (music, sfx):
    x[: int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))[:, None]
    x[-int(1.4 * SR):] *= (np.linspace(1, 0, int(1.4 * SR)) ** 1.6)[:, None]

# balance: music under, effects forward but blended; one master limiter for both stems
music *= 0.62
sfx *= 0.9
mix = music + sfx
peak_env = np.maximum.accumulate(np.abs(mix).max(1)[::-1])[::-1]  # crude look-ahead
win = int(0.006 * SR)
pk = np.convolve(np.abs(mix).max(1), np.ones(win), "same") / win
pk = np.maximum(pk, np.abs(mix).max(1))
ceiling = 10 ** (-1.5 / 20)
g = np.minimum(1, ceiling / np.maximum(pk, 1e-9))
g = lp(g, 30, order=1)
g = np.minimum(g, ceiling / np.maximum(np.abs(mix).max(1), 1e-9))
music *= g[:, None]
sfx *= g[:, None]
norm = 10 ** (-1.2 / 20) / max(1e-9, np.abs(music + sfx).max())
music *= min(1.0, norm)
sfx *= min(1.0, norm)


def write(path, x):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


proj = sys.argv[1] if len(sys.argv) > 1 else "."
write(os.path.join(proj, "assets", "audio", "music.wav"), music)
write(os.path.join(proj, "assets", "audio", "sfx.wav"), sfx)
with open(os.path.join(proj, "audio", "sound_cuesheet.md"), "w") as f:
    f.write("# Sound cue sheet (generated by audio/score.py)\n\n| time (s) | event |\n|---|---|\n")
    for t, what in sorted(CUES):
        f.write(f"| {t:.2f} | {what} |\n")
print(f"score -> music.wav + sfx.wav ({DUR} s), {len(CUES)} sound cues")
