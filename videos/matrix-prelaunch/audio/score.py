"""Matrix prelaunch film: original score + sound design, synthesized locally (numpy + scipy), seeded, $0.

    .claude/skills/motion-studio/scripts/py audio/score.py [project_dir]
      -> assets/audio/music.wav, assets/audio/sfx.wav (stems, already mastered together), audio/sound_cuesheet.md

Direction: one continuous song carries the film, in the warm, optimistic "AI launch film" style: a hook
melody sung by a wordless vocal-chop lead (doubled by felt piano and glass bells), an I-V-vi-IV progression in
D major, side-chained pads and bass, a four-on-the-floor chorus groove, and real song form
(intro, pre, chorus, verse, pre, chorus, bridge, build, final chorus). The tempo (~114 BPM) is set so the
chorus downbeats land on the film's turning points. Sound effects are side effects: few, soft, and tuned to
the key, under one shared reverb and one master limiter.

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


# ================================================================= THE SONG
# One continuous song is the red thread. The tempo (~114 BPM) is chosen so bar lines fall on the film's
# turning points: bar 5 = 11.00 "Now together" (chorus), bar 10 = 21.52 LP explainer (chorus 2),
# bar 13 = 27.83 summary, bar 17 = 36.25 end card (final chorus). Everything else follows the song.
BAR = (36.25 - 11.0) / 12
BEAT = BAR / 4
T0 = 11.0 - 5 * BAR  # bar 0 downbeat (0.48 s)
PUMP = Bus()         # pads + bass: side-chained to the kick (the modern "breathing" pulse)
KICKS = []


def bt(bar, beat=0.0):
    return T0 + bar * BAR + beat * BEAT


V = {  # voicings (mid register) and bass roots
    "D": ("D3 A3 E4 F#4", "D2"), "A/C#": ("E3 A3 C#4 E4", "C#2"), "Bm": ("B2 F#3 A3 D4", "B1"),
    "G": ("G2 D3 B3 F#4", "G1"), "Em": ("E3 G3 B3 D4", "E2"), "Asus": ("E3 A3 D4 E4", "A1"),
    "A": ("E3 A3 C#4 E4", "A1"), "D/F#": ("F#3 A3 D4 E4", "F#2"), "Dhi": ("D4 F#4 A4 C#5 E5", "D2")}

#        bar: chords (name, beats)            drums     bass      piano     arp
FORM = {
    0: ([("D", 4)],                 "none",   "none",   "intro",  None),
    1: ([("A/C#", 4)],              "none",   "none",   "intro",  None),
    2: ([("Bm", 4)],                "soft",   "whole",  "intro",  None),
    3: ([("G", 4)],                 "soft2",  "whole",  "intro",  "8th"),
    4: ([("Asus", 2), ("A", 2)],    "build",  "eighth", "build",  "16th"),
    5: ([("D", 4)],                 "full",   "eighth", "stabs",  "16th"),     # CHORUS 1 · Now together
    6: ([("Bm", 4)],                "half",   "half",   "verse",  None),       # verse · markets / downtrend
    7: ([("G", 4)],                 "half",   "half",   "verse",  "8th"),
    8: ([("D/F#", 4)],              "half",   "half",   "verse",  "8th"),
    9: ([("Em", 2), ("A", 2)],      "build",  "eighth", "build",  "16th"),     # pre · next move
    10: ([("D", 4)],                "full",   "eighth", "stabs",  "16th"),     # CHORUS 2 · exactly why
    11: ([("A/C#", 4)],             "full",   "eighth", "stabs",  "16th"),
    12: ([("Bm", 4)],               "full",   "eighth", "stabs",  "16th"),
    13: ([("G", 4)],                "full",   "eighth", "stabs",  "16th"),
    14: ([("Em", 4)],               "bridge", "whole",  "broken", "8th"),      # bridge · live Archive
    15: ([("G", 4)],                "bridge", "whole",  "broken", "8th"),
    16: ([("Asus", 2), ("A", 2)],   "build",  "eighth", "build",  "16th"),
    17: ([("D", 4)],                "full",   "eighth", "stabs",  "16th"),     # FINAL CHORUS · end card
    18: ([("Dhi", 4)],              "none",   "long",   "end",    None),
}

# the hook: a pickup (A-D-E) that always lands on F#; the same shape returns in every chorus
PICK = [(2.5, .5, "A4"), (3, .5, "D5"), (3.5, .5, "E5")]
MEL = {  # bar: [(beat, beats, note)]
    0: [(0, 2, "F#5"), (2, .5, "E5"), (2.5, .5, "D5"), (3, 1, "E5")],
    1: [(0, 1.5, "C#5"), (1.5, 1, "A4")] + PICK,
    2: [(0, 1.5, "F#5"), (1.5, 1, "A5"), (2.5, .5, "F#5"), (3, 1, "E5")],
    3: [(0, 1.5, "D5"), (1.5, .5, "B4"), (2, 2, "D5")],
    4: [(0, 1, "C#5"), (1, 1, "E5")] + PICK,
    5: [(0, 2, "F#5"), (2, .5, "E5"), (2.5, .5, "D5"), (3, 1, "E5")],
    6: [(0, 2, "D5"), (2, 1, "C#5"), (3, 1, "B4")],                          # verse: the line falls with the chart
    7: [(0, 1.5, "B4"), (1.5, .5, "A4"), (2, 2, "G4")],
    8: [(0, 3, "A4"), (3, 1, "F#4")],
    9: [(0, 1, "G4"), (1, 1, "B4")] + PICK,
    10: [(0, 2, "F#5"), (2, .5, "E5"), (2.5, .5, "D5"), (3, 1, "E5")],
    11: [(0, 1.5, "C#5"), (1.5, 1, "A4")] + PICK,
    12: [(0, .5, "F#5"), (.5, .5, "E5"), (1, .5, "D5"), (1.5, .5, "C#5"), (2, 1, "B4"), (3, 1, "A4")],  # price falls
    13: [(0, .5, "B4"), (.5, .5, "D5"), (1, 1, "F#5"), (2, 2, "A5")],        # ...the stack grows: lifts on the summary
    14: [(0, 1, "B4"), (1, 1, "D5"), (2, 2, "E5")],                           # bridge (bells + piano)
    15: [(0, 1, "D5"), (1, 1, "B4"), (2, 2, "D5")],
    16: [(0, 1, "C#5"), (1, 1, "E5")] + PICK,
    17: [(0, 2, "F#5"), (2, .5, "E5"), (2.5, 1.5, "D5")],
    18: [(0, 4, "D5")],
}
VOX_BARS = {4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16, 17, 18}
BELL_BARS = {10, 11, 12, 13, 14, 15, 17}


def vox(f, dur, vel=1.0, vowel="ah", seed=0):
    """Wordless vocal-chop lead: band-limited saw through vowel formants, scoop + delayed vibrato."""
    t = tt(dur + 0.25)
    vib = 0.012 * np.clip((t - 0.22) / 0.3, 0, 1) * np.sin(2 * np.pi * 5.3 * t)
    ff = f * (1 + vib) * 2 ** (-0.9 / 12 * np.exp(-t / 0.035))
    ph = 2 * np.pi * np.cumsum(ff) / SR
    saw = np.zeros(len(t))
    for k in range(1, 40):
        if k * f > 6500:
            break
        saw += np.sin(k * ph) / k
    F = {"ah": ((730, 1.0), (1090, .55), (2440, .25)), "oh": ((570, 1.0), (840, .5), (2410, .2)),
         "oo": ((330, 1.0), (870, .35), (2240, .12)), "eh": ((530, 1.0), (1840, .45), (2480, .25))}[vowel]
    s = sum(g * bp(saw, fc * 0.8, fc * 1.22) for fc, g in F) + 0.12 * saw
    e = adsr(len(t), 0.025, 0.15, 0.85, 0.22)
    return lp(s * e * vel * 0.6, 7000)


def crash(dur=3.0, seed=0):
    r = np.random.default_rng(seed)
    t = tt(dur)
    return hp(r.standard_normal(len(t)), 4500) * np.exp(-t * 1.6) * np.minimum(1, t / 0.003) * 0.12


def reverse_cymbal(dur=1.2, seed=0):
    return crash(dur, seed)[::-1].copy() * 1.4


def hat(vel=1.0, seed=0, open_=False):
    r = np.random.default_rng(seed)
    t = tt(0.3 if open_ else 0.07)
    return hp(r.standard_normal(len(t)), 7500) * np.exp(-t * (11 if open_ else 70)) * vel * 0.16


def snare(vel=1.0, seed=0):
    r = np.random.default_rng(seed)
    t = tt(0.2)
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.4
    return (body + bp(r.standard_normal(len(t)), 1500, 8000) * np.exp(-t * 22)) * vel * 0.22


def K(t, vel=1.0, seed=0):
    place(MUS, kick(vel, seed), t, 0.62, verb=0.0)
    KICKS.append(t)


# ----------------------------------------------------------------- arrange bar by bar
for bar, (chords, drum, bass, piano, arpm) in FORM.items():
    b0 = bt(bar)
    beat_at = 0.0
    for ci, (name, beats) in enumerate(chords):
        notes, root = V[name]
        fs = chord(notes)
        t = bt(bar, beat_at)
        dur = beats * BEAT
        seed = bar * 10 + ci
        # pad (on the pumped bus) — brightness follows the energy of the section
        bright = {"none": 1200, "soft": 1400, "soft2": 1600, "half": 1500, "bridge": 1900, "build": 2600, "full": 3000}[drum]
        pg = 0.34 if drum in ("none", "soft") else 0.4
        if bar == 18:
            place(PUMP, pad(fs, 4.2, 0.05, 2.6, 2600, seed), t, 0.5, verb=0.7)
        else:
            place(PUMP, pad(fs, dur + 0.35, 0.25 if bar else 1.2, 0.5, bright, seed), t, pg, verb=0.55)
        # bass
        rf = note(root)
        if bass == "whole":
            place(PUMP, 0.75 * sub(rf, dur, 0.55), t, 0.55, verb=0.0)
        elif bass == "half":
            place(PUMP, 0.75 * sub(rf, 1.4 * BEAT, 0.6), t, 0.55, verb=0.0)
            place(PUMP, 0.75 * sub(rf, 1.4 * BEAT, 0.5), t + 1.5 * BEAT, 0.55, verb=0.0)
        elif bass == "eighth":
            for k in range(int(beats * 2)):
                f = rf * (2 if k % 4 == 3 else 1)
                place(PUMP, 0.75 * sub(f, 0.45 * BEAT, 0.62 if k % 2 else 0.5), t + k * BEAT / 2, 0.55, verb=0.0)
        elif bass == "long":
            place(PUMP, 0.75 * sub(rf, 3.8, 0.6), t, 0.55, verb=0.0)
        # piano
        if piano in ("intro", "verse", "end"):
            piano_vel = {"intro": 0.5, "verse": 0.55, "end": 0.7}[piano]
            for k, f in enumerate(fs):
                place(MUS, felt_piano(f, min(3.2, dur + 1.0), piano_vel * (1 if k == 0 else 0.8), seed=seed * 7 + k),
                      t + k * 0.03, 0.42, pan=-0.3 + 0.6 * k / len(fs), verb=0.45)
        elif piano == "stabs":   # off-beat chord pulses: the rhythmic heartbeat of the chorus
            for k in range(int(beats)):
                for j, f in enumerate(fs[1:]):
                    place(MUS, felt_piano(f, 0.55, 0.5, seed=seed * 13 + k * 5 + j), t + (k + 0.5) * BEAT, 0.3,
                          pan=-0.25 + 0.5 * j / 3, verb=0.35)
        elif piano == "broken":
            for k in range(int(beats * 2)):
                f = sorted(fs)[[0, 2, 1, 3, 2, 3, 1, 2][k % 8]] * 2
                place(MUS, felt_piano(f, 1.4, 0.45, seed=seed * 17 + k), t + k * BEAT / 2, 0.36,
                      pan=0.35 * (1 if k % 2 else -1), verb=0.5, dly=0.2)
        elif piano == "build":
            for k, f in enumerate(fs):
                place(MUS, felt_piano(f, dur + 0.3, 0.55, seed=seed * 19 + k), t + k * 0.02, 0.38, verb=0.45)
        # arp plucks (16ths in the chorus, 8ths elsewhere), with the tempo delay
        if arpm:
            step = BEAT / (4 if arpm == "16th" else 2)
            srt = sorted(fs)
            pat = (0, 2, 1, 3, 2, 3, 1, 2)
            for k in range(int(round(dur / step))):
                f = srt[pat[k % 8] % len(srt)] * 2
                v = 0.42 * (1.0 if k % 4 == 0 else 0.72)
                place(MUS, pluck(f, 0.3, v, 3200 if drum == "full" else 2200, seed * 31 + k), t + k * step,
                      0.3 if drum == "full" else 0.26, pan=0.45 * (1 if k % 2 else -1), verb=0.25, dly=0.25)
        beat_at += beats

    # drums
    s = bar * 100
    if drum in ("soft", "soft2"):
        for k in (0, 2):
            K(bt(bar, k), 0.45, s + k)
        for k in range(8):
            place(MUS, shaker(0.6 + 0.4 * (k % 2), s + 20 + k), bt(bar, k / 2), 0.45, pan=0.35, verb=0.15)
        if drum == "soft2":
            for k in (1, 3):
                place(MUS, snap(0.8, s + 40 + k), bt(bar, k), 0.45, pan=-0.1, verb=0.35)
    elif drum == "full":
        for k in range(4):
            K(bt(bar, k), 0.85, s + k)
            place(MUS, hat(0.9, s + 10 + k, open_=True), bt(bar, k + 0.5), 0.5, pan=0.2, verb=0.1)
        for k in (1, 3):
            place(MUS, clap(0.9, s + 30 + k), bt(bar, k), 0.6, pan=0.05, verb=0.35)
        for k in range(16):
            place(MUS, shaker(0.5 + 0.5 * (k % 2), s + 50 + k), bt(bar, k / 4), 0.35, pan=-0.35, verb=0.1)
    elif drum == "half":
        K(bt(bar, 0), 0.7, s); K(bt(bar, 2.5), 0.55, s + 1)
        place(MUS, clap(0.75, s + 2), bt(bar, 2), 0.55, verb=0.4)
        for k in range(16):
            place(MUS, shaker(0.35 + 0.4 * (k % 2), s + 50 + k), bt(bar, k / 4), 0.32, pan=0.35, verb=0.1)
    elif drum == "bridge":
        for k in (0, 2):
            K(bt(bar, k), 0.6, s + k)
        for k in range(4):
            place(MUS, hat(0.7, s + 10 + k), bt(bar, k + 0.5), 0.45, pan=0.25, verb=0.1)
        place(MUS, snap(0.8, s + 30), bt(bar, 3), 0.4, verb=0.4)
    elif drum == "build":
        for k in range(3):
            K(bt(bar, k), 0.7, s + k)
        n = 0
        for k, (a, step) in enumerate(((0, .5), (1, .5), (2, .25))):        # snare roll accelerates; beat 4 breathes
            for j in range(int(1 / step)):
                tb = a + j * step
                place(MUS, snare(0.25 + 0.6 * (tb / 3) ** 1.5, s + 60 + n), bt(bar, tb), 0.5, pan=0.1 * (-1) ** n, verb=0.35)
                n += 1
        place(MUS, riser(BAR * 0.95, 300, 7000, seed=s + 90), bt(bar, 0), 0.4, verb=0.4)
        place(MUS, reverse_cymbal(1.2, s + 91), bt(bar + 1) - 1.2, 0.8, verb=0.2)

    if drum == "full" and FORM.get(bar - 1, (0, ""))[1] != "full":
        place(MUS, crash(3.0, s + 95), bt(bar), 0.9, verb=0.4)

    # the hook: vocal-chop lead (+ piano double, + bells an octave up in the big moments)
    vowels = ["ah", "oh", "ah", "eh", "oo"]
    for k, (b, d, n) in enumerate(MEL.get(bar, [])):
        t = bt(bar, b)
        f = note(n)
        dd = d * BEAT * 0.95 if bar != 18 else 3.6
        if bar in VOX_BARS:
            place(MUS, vox(f, dd, 0.9, vowels[(bar + k) % 5], bar * 50 + k), t, 0.62, pan=0.0, verb=0.4, dly=0.18)
        place(MUS, felt_piano(f, max(1.2, dd + 0.6), 0.75 if bar not in VOX_BARS else 0.45, seed=bar * 70 + k),
              t, 0.48 if bar not in VOX_BARS else 0.26, pan=-0.12, verb=0.45, dly=0.12)
        if bar in BELL_BARS:
            place(MUS, bell(f * 2, 1.8, 0.5), t, 0.18 if bar not in (14, 15) else 0.3, pan=0.3, verb=0.6, dly=0.3)

# a soft breath in before the first note
place(MUS, reverse_swell(felt_piano(note("D4"), 0.9, 0.6, seed=1)), 0.0, 0.25, verb=0.5)
place(PUMP, pad(chord("D3 A3 E4"), 1.0, 0.6, 0.4, 1000, 99), 0.0, 0.25, verb=0.5)

# side-chain: pads and bass duck on every kick and swell back between them
pump = np.ones(N)
for tk in KICKS:
    i = int(tk * SR)
    n = min(N - i, int(0.45 * SR))
    if n > 0:
        x = np.arange(n) / SR
        pump[i:i + n] = np.minimum(pump[i:i + n], 1 - 0.55 * np.exp(-x / 0.11))
pump = lp(pump, 60, order=1)
MUS.dry += PUMP.dry * pump[:, None]
MUS.verb += PUMP.verb * pump[:, None]
cue(0.48, "SONG · intro (piano states the hook)")
cue(bt(4), "SONG · pre-chorus build")
cue(bt(5), "SONG · CHORUS 1 lands with 'Now together'")
cue(bt(6), "SONG · half-time verse under the downtrend")
cue(bt(9), "SONG · pre-chorus 2")
cue(bt(10), "SONG · CHORUS 2 (LP explainer); the hook falls with the price, lifts on the summary")
cue(bt(14), "SONG · bridge (live Archive)")
cue(bt(16), "SONG · build")
cue(bt(17), "SONG · FINAL CHORUS on the end card, rings out")

# ================================================================= SOUND DESIGN (side effects: few, soft, tuned)
def W(t_peak, dur, gain, p0, p1, seed, verb=0.3, lo=None, hi=None, label=""):
    m = whoosh(dur, seed, lo, hi)
    place(SFX, stereo_sweep(m, p0, p1), t_peak - dur * 0.57, gain, verb=verb)
    cue(t_peak, "sfx whoosh · " + label)


def G(t, f, gain, pan, seed, label="", verb=0.45, dly=0.2):
    place(SFX, glass(f, 0.9, 1.0, seed), t, gain, pan=pan, verb=verb, dly=dly)
    cue(t, "sfx glass · " + label)


for k, n in enumerate(["A5", "C#6", "E6", "F#6"]):
    G(1.0 + k, note(n), 0.3, -0.15 + 0.1 * k, 50 + k, f"tab {k + 1}")
W(6.45, 1.0, 0.3, 0.3, -0.7, 90, verb=0.4, lo=150, hi=2200, label="zoom out")
W(7.5, 0.8, 0.22, 0.9, 0.4, 91, label="market tabs swing in")
W(9.95, 0.9, 0.32, -0.4, 0.4, 100, verb=0.35, label="tabs fly into the mosaic")
for k, t in enumerate([10.22, 10.33, 10.46, 10.57, 10.66, 10.78]):
    place(SFX, ui_click(110 + k, pitch=1400 + 180 * k), t, 0.14, pan=-0.5 + 0.2 * k, verb=0.2)
cue(10.3, "sfx · six tiles lock")
place(SFX, boom(2.0, 46), 11.0, 0.4, verb=0.25)
place(SFX, air_impact(130), 11.0, 0.4, verb=0.6); cue(11.0, "sfx · soft impact under the chorus hit")
W(13.85, 0.9, 0.26, -0.4, 0.4, 140, verb=0.4, label="rectangle opens into the window")
place(SFX, soft_pop(note("G4")), 17.15, 0.16, verb=0.4); cue(17.15, "sfx pop · Bear market lands")
place(SFX, soft_pop(note("A4")), 19.3, 0.16, verb=0.4); cue(19.3, "sfx pop · Asset accumulation card")
for k, n in enumerate(["D6", "F#6", "A6"]):
    G(19.75 + 0.12 * k, note(n), 0.1, -0.3 + 0.3 * k, 148 + k, f"chip {k + 1}")
W(21.85, 0.8, 0.26, 0.2, -0.3, 150, verb=0.35, label="card opens into the LP explainer")
place(SFX, soft_pop(note("D5")), 22.75, 0.16, pan=0.5, verb=0.3); cue(22.75, "sfx pop · deposit")
for k, n in enumerate(["D6", "C#6", "B5", "A5", "G5", "F#5", "E5", "D5"]):
    t = 23.65 + k * 0.1
    place(SFX, glass(note(n), 0.5, 0.7, 160 + k), t, 0.12, pan=-0.35 + 0.08 * k, verb=0.35, dly=0.1)
cue(23.65, "sfx · USDC coins land (falling D-major scale)")
fee_t = [24.2, 24.387, 24.574, 24.761, 24.948, 25.135, 25.322, 25.509, 25.696, 25.883]
fee_n = ["D6", "E6", "F#6", "A6", "B6", "D7", "B6", "D7", "E7", "F#7"]
for k, (ts, n) in enumerate(zip(fee_t, fee_n)):
    place(SFX, glass(note(n), 0.6, 0.8, 190 + k), ts + 0.7, 0.09, pan=0.55 - 0.05 * k, verb=0.4, dly=0.15)
cue(24.9, "sfx · fee coins climb (soft)")
for k, n in enumerate(["D5", "F#5", "A5"]):
    place(SFX, soft_pop(note(n)), 27.85 + 0.15 * k, 0.14, pan=-0.3 + 0.3 * k, verb=0.35)
cue(27.85, "sfx pops · summary chips")
W(29.82, 0.9, 0.28, 0.3, -0.3, 210, verb=0.4, label="window becomes the live Archive")
for k, (t, label) in enumerate([(30.7, "ENTER THE ARCHIVE"), (31.8, "Bear"), (32.9, "OPEN RECORD")]):
    place(SFX, ui_click(220 + k, pitch=[2300, 2000, 2500][k]), t, 0.32, pan=-0.1 + 0.1 * k, verb=0.2)
    cue(t, "sfx click · " + label)
W(33.9, 0.8, 0.2, -0.2, 0.3, 240, label="zoom into the Overview")
W(36.1, 0.7, 0.26, 0.4, 0.0, 250, label="window collapses into the mark")
place(SFX, boom(1.6, 50), 36.25, 0.25, verb=0.3); cue(36.25, "sfx · soft sub as the mark lands")

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

# the song leads; effects sit inside it (no big ducks)
duck = np.ones(N)
for t, depth, rel in ((30.7, 0.88, 0.3), (31.8, 0.88, 0.3), (32.9, 0.88, 0.3)):  # only a breath for the archive clicks
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
music = music + 1.0 * hp(music, 2800) + 0.5 * hp(music, 7000)  # air: the bright, open launch-film top end
for x in (music, sfx):
    x[: int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))[:, None]
    x[-int(1.4 * SR):] *= (np.linspace(1, 0, int(1.4 * SR)) ** 1.6)[:, None]

# balance: the song is the red thread, effects are side effects; one master limiter for both stems
music *= 0.66
sfx *= 1.2
mix = music + sfx
peak_env = np.maximum.accumulate(np.abs(mix).max(1)[::-1])[::-1]  # crude look-ahead
win = int(0.006 * SR)
pk = np.convolve(np.abs(mix).max(1), np.ones(win), "same") / win
pk = np.maximum(pk, np.abs(mix).max(1))
ceiling = 10 ** (-2.6 / 20)
g = np.minimum(1, ceiling / np.maximum(pk, 1e-9))
g = lp(g, 30, order=1)
g = np.minimum(g, ceiling / np.maximum(np.abs(mix).max(1), 1e-9))
music *= g[:, None]
sfx *= g[:, None]
norm = 10 ** (-3.0 / 20) / max(1e-9, np.abs(music + sfx).max())
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
