"""Procedural sound-effect synthesis (numpy only, 48 kHz stereo, deterministic). No downloads, no licences:
every effect is math. Built for the "One Conversation" film (375 cues) and reused since.

Every generator returns a float32 array of shape (n, 2). Randomness always comes from a seeded Generator,
so the same cue file always renders the same audio.

  key       keyboard click (heavy=True for space/enter)      whoosh   band-swept noise pass (pan_from/pan_to, dur)
  pop       UI pop (f0 -> f1 chirp)                           impact   low cinematic impact with tail
  blip      tiny UI blip (freq)                               boom     the big one: sub boom for a drop
  chime     two-note notification (freqs)                     glitch   bit-crushed gated crunch
  error     error buzz                                        riser    noise + tone riser (dur, f0, f1); use align "end"
  swell     reverse swell into a hit; use align "end"         tapestop pitch collapsing to zero (time freezes)
  paper     paper / page movement                             tick     clock / counter tick (freq)
  snap      magnetic snap (timeline clip landing)             shimmer  airy sparkle bed (dur, base)
  subdrop   sub-bass drop under a hit                         shutter  camera shutter / frame tick
  room_tone(dur) is the quiet background bed (used by build_sfx.py "room_env").
"""

import numpy as np

SR = 48000


def rng(seed):
    return np.random.default_rng(seed)


def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def stereo(mono, pan=0.0):
    """Equal-power pan, pan in [-1, 1]."""
    a = (pan + 1) * np.pi / 4
    return np.stack([mono * np.cos(a), mono * np.sin(a)], axis=1).astype(np.float32)


def env_adsr(n, a=0.005, d=0.05, s=0.0, r=0.05, hold=0.0):
    out = np.zeros(n)
    ia, idd, ih, ir = int(a * SR), int(d * SR), int(hold * SR), int(r * SR)
    i = 0
    seg = min(ia, n - i)
    out[i : i + seg] = np.linspace(0, 1, ia, endpoint=False)[:seg]
    i += seg
    seg = min(idd, n - i)
    out[i : i + seg] = np.linspace(1, s, idd, endpoint=False)[:seg] if s > 0 else np.exp(-np.linspace(0, 5, idd))[:seg]
    i += seg
    seg = min(ih, n - i)
    out[i : i + seg] = s if s > 0 else out[i - 1] if i > 0 else 0
    i += seg
    if i < n:
        start = out[i - 1] if i > 0 else 0
        rr = n - i
        out[i:] = start * np.exp(-np.linspace(0, 6, rr)) * (np.linspace(1, 0, rr) ** 0.5)
    return out


def fft_filter(x, lo=None, hi=None, order=2):
    """Zero-phase brickwall-ish band filter with smooth (butterworth-shaped) magnitude."""
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    h = np.ones_like(f)
    if lo:
        h *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (2 * order))
    if hi:
        h *= 1 / np.sqrt(1 + (f / hi) ** (2 * order))
    return np.fft.irfft(X * h, n)


def time_varying_bandpass(x, centers, q=2.0, block=1024):
    """Overlap-add STFT bandpass whose centre follows `centers` (array len(x))."""
    n = len(x)
    out = np.zeros(n + block)
    win = np.hanning(block)
    hop = block // 2
    f = np.fft.rfftfreq(block, 1 / SR)
    for i in range(0, n, hop):
        seg = x[i : i + block]
        if len(seg) < block:
            seg = np.pad(seg, (0, block - len(seg)))
        c = centers[min(i + hop, n - 1)]
        bw = c / q
        h = np.exp(-0.5 * ((f - c) / bw) ** 2)
        out[i : i + block] += np.fft.irfft(np.fft.rfft(seg * win) * h, block)
    return out[:n]


def reverb(st, decay=1.6, mix=0.3, seed=7, predelay=0.012, tone=6000):
    """Convolution with a synthetic decaying-noise IR (decorrelated L/R)."""
    r = rng(seed)
    n_ir = int(decay * SR)
    tt = np.arange(n_ir) / SR
    envl = np.exp(-6.9 * tt / decay)
    out = np.zeros((len(st) + n_ir + int(predelay * SR), 2))
    for ch in range(2):
        ir = r.standard_normal(n_ir) * envl
        ir = fft_filter(ir, lo=200, hi=tone)
        ir /= np.sqrt(np.sum(ir**2)) + 1e-9
        ir = np.concatenate([np.zeros(int(predelay * SR)), ir])
        m = len(st) + len(ir) - 1
        nfft = 1 << (m - 1).bit_length()
        wet = np.fft.irfft(np.fft.rfft(st[:, ch], nfft) * np.fft.rfft(ir, nfft), nfft)[:m]
        out[: len(wet), ch] += wet * mix
        out[: len(st), ch] += st[:, ch] * (1 - mix * 0.5)
    return out.astype(np.float32)


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) + 1e-9
    return (x / m * peak).astype(np.float32)


# ----------------------------------------------------------------------------- generators


def key_click(seed=0, heavy=False):
    r = rng(seed)
    dur = 0.09 if not heavy else 0.14
    t = t_axis(dur)
    n = len(t)
    noise = r.standard_normal(n)
    click = fft_filter(noise, lo=1800 + r.uniform(-300, 300), hi=7000) * np.exp(-t / 0.004)
    thock_f = (150 if heavy else 210) * r.uniform(0.9, 1.1)
    thock = np.sin(2 * np.pi * thock_f * t) * np.exp(-t / (0.022 if heavy else 0.014)) * 0.8
    rattle = fft_filter(noise, lo=600, hi=2500) * np.exp(-((t - 0.012) ** 2) / 0.00002) * 0.25
    up = np.zeros(n)
    k = int(r.uniform(0.045, 0.06) * SR)  # key release tick
    if k < n:
        up[k:] = fft_filter(r.standard_normal(n - k), lo=2500, hi=8000) * np.exp(-np.arange(n - k) / SR / 0.003) * 0.35
    mono = click * 0.9 + thock + rattle + up
    return stereo(norm(mono, 0.8), pan=r.uniform(-0.25, 0.25))


def ui_pop(f0=520, f1=1250, dur=0.12, seed=1, pan=0.0):
    t = t_axis(dur)
    f = f0 + (f1 - f0) * (1 - np.exp(-t / 0.018))
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) * np.exp(-t / 0.035)
    tick = fft_filter(rng(seed).standard_normal(len(t)), lo=3000) * np.exp(-t / 0.002) * 0.3
    return stereo(norm(tone + tick, 0.7), pan)


def blip(freq=1320, dur=0.07, pan=0.0, seed=2):
    t = t_axis(dur)
    tone = (np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * freq * 2 * t)) * env_adsr(len(t), 0.002, 0.03, 0.3, 0.03)
    return stereo(norm(tone, 0.5), pan)


def chime(freqs=(880, 1318.5), gap=0.09, seed=3, pan=0.0):
    out = np.zeros(int(0.9 * SR))
    for i, f in enumerate(freqs):
        t = t_axis(0.8)
        s = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.05)) * np.exp(-t / 0.22)
        k = int(i * gap * SR)
        out[k : k + len(s)] += s[: len(out) - k]
    return reverb(stereo(norm(out, 0.5), pan), decay=0.9, mix=0.25, seed=seed)


def whoosh(dur=0.6, f_lo=250, f_hi=4200, pan_from=-0.7, pan_to=0.7, seed=4, peak_at=0.55):
    r = rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = r.standard_normal(n)
    p = t / dur
    shape = np.where(p < peak_at, (p / peak_at) ** 2.2, ((1 - p) / (1 - peak_at)) ** 1.4)
    centers = f_lo + (f_hi - f_lo) * shape
    band = time_varying_bandpass(x, centers, q=1.6)
    amp = shape**1.3
    mono = band * amp
    mono += fft_filter(r.standard_normal(n), hi=180) * amp * 0.6  # body
    pans = pan_from + (pan_to - pan_from) * p
    a = (pans + 1) * np.pi / 4
    st = np.stack([mono * np.cos(a), mono * np.sin(a)], axis=1)
    return norm(st, 0.8).astype(np.float32)


def impact_low(seed=5, dur=2.6, f0=62, f1=31):
    r = rng(seed)
    t = t_axis(dur)
    f = f1 + (f0 - f1) * np.exp(-t / 0.18)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.75)
    thump = fft_filter(r.standard_normal(len(t)), hi=900) * np.exp(-t / 0.05)
    crack = fft_filter(r.standard_normal(len(t)), lo=1500, hi=9000) * np.exp(-t / 0.012) * 0.6
    mono = np.tanh(1.6 * (sub * 1.0 + thump * 0.7 + crack))
    return reverb(stereo(norm(mono, 0.95)), decay=2.4, mix=0.35, seed=seed, tone=3500)


def boom(seed=6, dur=4.5):
    r = rng(seed)
    t = t_axis(dur)
    f = 28 + 46 * np.exp(-t / 0.25)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 1.4)
    body = fft_filter(r.standard_normal(len(t)), hi=400) * np.exp(-t / 0.35) * 0.8
    air = fft_filter(r.standard_normal(len(t)), lo=2000, hi=12000) * np.exp(-t / 0.5) * 0.25
    tok = np.sin(2 * np.pi * 140 * t) * np.exp(-t / 0.03)
    mono = np.tanh(1.4 * (sub + body + air + tok * 0.6))
    return reverb(stereo(norm(mono, 0.97)), decay=3.8, mix=0.4, seed=seed, tone=5000)


def glitch_crunch(seed=8, dur=0.22, pan=0.0):
    r = rng(seed)
    n = int(dur * SR)
    x = r.standard_normal(n)
    hold = r.integers(8, 40)
    x = np.repeat(x[::hold], hold)[:n]  # sample-rate reduction
    x = np.round(x * 3) / 3  # bit crush
    gate = np.zeros(n)
    i = 0
    while i < n:
        on = int(r.uniform(0.008, 0.04) * SR)
        off = int(r.uniform(0.004, 0.02) * SR)
        gate[i : i + on] = 1
        i += on + off
    buzz = np.sign(np.sin(2 * np.pi * r.uniform(90, 160) * np.arange(n) / SR)) * 0.4
    mono = (x * 0.7 + buzz) * gate * env_adsr(n, 0.001, dur * 0.6, 0.4, dur * 0.3)
    mono = fft_filter(mono, lo=120, hi=9000)
    return stereo(norm(mono, 0.6), pan)


def error_buzz(seed=9, dur=0.28, pan=0.0):
    t = t_axis(dur)
    sq = np.sign(np.sin(2 * np.pi * 196 * t)) * 0.5 + np.sign(np.sin(2 * np.pi * 233 * t)) * 0.4
    trem = 0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 22 * t))
    mono = fft_filter(sq * trem, hi=3500) * env_adsr(len(t), 0.003, 0.05, 0.7, 0.08, hold=dur - 0.14)
    return stereo(norm(mono, 0.45), pan)


def riser(dur=4.0, seed=10, f0=180, f1=2400):
    r = rng(seed)
    t = t_axis(dur)
    p = t / dur
    amp = p**2.4
    noise = r.standard_normal(len(t))
    centers = 400 + 9000 * p**2
    hiss = time_varying_bandpass(noise, centers, q=1.2) * amp
    f = f0 * (f1 / f0) ** (p**1.6)
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = (np.sin(ph) + 0.5 * np.sin(ph * 1.5) + 0.3 * np.sin(ph * 2.01)) * amp * 0.35
    st = stereo(hiss + tone)
    # widen: slight delay on R
    d = int(0.011 * SR)
    st[d:, 1] = st[:-d, 1]
    return norm(st, 0.75)


def reverse_swell(dur=1.6, seed=11, freq=110):
    t = t_axis(dur)
    tone = sum(np.sin(2 * np.pi * freq * m * t + m) / m for m in (1, 2, 3, 4.01, 6.02))
    noise = fft_filter(rng(seed).standard_normal(len(t)), lo=300, hi=6000) * 0.5
    st = reverb(stereo((tone + noise) * np.exp(-t / 0.4)), decay=dur, mix=0.7, seed=seed)
    st = st[: len(t)][::-1]
    fade = np.linspace(0, 1, len(t)) ** 2
    return norm(st * fade[:, None], 0.75)


def tape_stop(dur=0.7, seed=12):
    """A whoosh whose pitch collapses to zero: time freezing."""
    r = rng(seed)
    t = t_axis(dur)
    p = t / dur
    rate = (1 - p) ** 1.8
    f = 220 * rate + 1
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = (np.sin(ph) + 0.4 * np.sin(2 * ph)) * (1 - p) ** 0.6
    noise = time_varying_bandpass(r.standard_normal(len(t)), 300 + 5000 * rate, q=1.3) * (1 - p)
    return stereo(norm(tone * 0.7 + noise, 0.7))


def paper(seed=13, dur=0.35, pan=0.0):
    r = rng(seed)
    n = int(dur * SR)
    x = r.standard_normal(n)
    grains = np.zeros(n)
    for _ in range(18):
        k = r.integers(0, n - 800)
        grains[k : k + 800] += np.hanning(800) * r.uniform(0.3, 1)
    mono = fft_filter(x, lo=1500, hi=9000) * grains * env_adsr(n, 0.02, dur * 0.5, 0.3, dur * 0.3)
    return stereo(norm(mono, 0.5), pan)


def tick(seed=14, freq=2600, pan=0.0):
    t = t_axis(0.05)
    mono = np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.006) + fft_filter(rng(seed).standard_normal(len(t)), lo=3000) * np.exp(-t / 0.002) * 0.4
    return stereo(norm(mono, 0.5), pan)


def snap_clip(seed=15, pan=0.0):
    """Magnetic timeline snap: low thock + click."""
    t = t_axis(0.12)
    mono = np.sin(2 * np.pi * 95 * t) * np.exp(-t / 0.03) + fft_filter(rng(seed).standard_normal(len(t)), lo=2000, hi=8000) * np.exp(-t / 0.004) * 0.6
    return stereo(norm(mono, 0.65), pan)


def shimmer(dur=3.0, seed=16, base=880):
    t = t_axis(dur)
    out = np.zeros(len(t))
    r = rng(seed)
    for m in (1, 1.5, 2, 2.5, 3, 4):
        out += np.sin(2 * np.pi * base * m * t + r.uniform(0, 6)) * (0.6 + 0.4 * np.sin(2 * np.pi * r.uniform(3, 7) * t)) / m
    envl = np.minimum(1, t / (dur * 0.35)) * np.exp(-np.maximum(0, t - dur * 0.4) / (dur * 0.3))
    return reverb(stereo(norm(out * envl, 0.35)), decay=2.0, mix=0.5, seed=seed)


def sub_drop(seed=17, dur=1.2):
    t = t_axis(dur)
    f = 30 + 90 * np.exp(-t / 0.12)
    mono = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.4)
    return stereo(norm(np.tanh(1.5 * mono), 0.9))


def shutter(seed=18, pan=0.0):
    r = rng(seed)
    t = t_axis(0.09)
    a = fft_filter(r.standard_normal(len(t)), lo=1200, hi=7000) * np.exp(-t / 0.006)
    b = np.zeros(len(t))
    k = int(0.035 * SR)
    b[k:] = fft_filter(r.standard_normal(len(t) - k), lo=900, hi=5000) * np.exp(-np.arange(len(t) - k) / SR / 0.008) * 0.7
    return stereo(norm(a + b, 0.5), pan)


def room_tone(dur, seed=19):
    r = rng(seed)
    n = int(dur * SR)
    brown = np.cumsum(r.standard_normal(n))
    brown = fft_filter(brown - np.convolve(brown, np.ones(4801) / 4801, "same"), lo=40, hi=900)
    air = fft_filter(r.standard_normal(n), lo=2000, hi=7000) * 0.05
    t = np.arange(n) / SR
    lfo = 0.8 + 0.2 * np.sin(2 * np.pi * 0.07 * t)
    hum = 0.04 * np.sin(2 * np.pi * 58 * t) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.13 * t))  # distant fridge
    mono = norm(brown, 1) * lfo + air + hum
    st = np.stack([mono, np.roll(mono, 1777)], axis=1)
    return norm(st, 0.5)


GENERATORS = {
    "key": key_click,
    "pop": ui_pop,
    "blip": blip,
    "chime": chime,
    "whoosh": whoosh,
    "impact": impact_low,
    "boom": boom,
    "glitch": glitch_crunch,
    "error": error_buzz,
    "riser": riser,
    "swell": reverse_swell,
    "tapestop": tape_stop,
    "paper": paper,
    "tick": tick,
    "snap": snap_clip,
    "shimmer": shimmer,
    "subdrop": sub_drop,
    "shutter": shutter,
}
