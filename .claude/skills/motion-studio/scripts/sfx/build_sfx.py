"""Render the sound-design layer of a project from a cue list. numpy only, deterministic.

  python build_sfx.py <project> [--duration S]

Reads  <project>/audio/sfx_cues.json
       <project>/compositions/**/<scene>.motion.json   (optional: events each scene reports, see below)
Writes <project>/assets/audio/<bus>.wav       one stereo stem per bus (default bus "sfx")
       <project>/assets/audio/room.wav        if "room_env" is given (quiet room tone with its own envelope)
       <project>/audio/sfx_cuesheet.md        every effect, its time and what it sits under

sfx_cues.json:
{
  "duration": 68.5,                       // film length (or pass --duration; else audio/timing.json duration)
  "room_env": [[0, 0.9], [18.4, 0], ...], // optional [t, gain] keyframes for room tone
  "cues": [
    {"t": 16.031, "fx": "impact", "gain_db": -1, "label": "the answer lands"},
    {"t": 50.031, "fx": "riser", "gain_db": -4, "align": "end", "args": {"dur": 5.6}, "label": "riser INTO the drop"},
    {"t": 18.0, "fx": "whoosh", "gain_db": -7, "peak": true, "args": {"dur": 0.75}, "label": "push-through on the seam"},
    {"t": 34.0, "fx": "pop", "gain_db": -9, "bus": "ui"}
  ],
  "slots": {"04-writer": 17.631},          // optional: scene id -> global start, to place scene events
  "event_kinds": {"key": ["key", -17, {}]} // optional: override the default event kind -> effect map
}
align "end": the sound ENDS at t (risers and reverse swells into a hit). "peak": true: a whoosh PEAKS at t.

Scene events: a scene worker writes compositions/frames/<id>.motion.json with
  {"events": [{"t": 1.25, "kind": "key", "note": "typed H"}, ...]}   (t is local to the scene)
and every event becomes a cue at slots[id] + t, so every keystroke and landing gets its sound.
"""

import argparse
import glob
import json
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfx_lib as L  # noqa: E402

KIND = {  # event kind -> (effect, gain dB, args)
    "key": ("key", -17, {}),
    "key_heavy": ("key", -15, {"heavy": True}),
    "backspace": ("key", -18, {}),
    "pop": ("pop", -16, {}),
    "land": ("snap", -14, {}),
    "slam": ("glitch", -12, {"dur": 0.2}),
    "error": ("error", -16, {}),
    "notify": ("chime", -19, {}),
    "stamp": ("impact", -9, {"dur": 1.2}),
    "snap": ("snap", -13, {}),
    "tick": ("tick", -19, {}),
    "shutter": ("shutter", -18, {}),
    "whoosh": ("whoosh", -14, {"dur": 0.45}),
    "marker": ("paper", -15, {"dur": 0.25}),
    "paper": ("paper", -15, {}),
    "glitch": ("glitch", -14, {}),
    "blip": ("blip", -20, {}),
    "impact": ("impact", -6, {}),
    "boom": ("boom", -2, {}),
    "chime": ("chime", -14, {}),
    "shimmer": ("shimmer", -12, {}),
}
SEEDED = {"key", "glitch", "paper", "whoosh", "tick", "snap", "shutter"}

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--duration", type=float)
a = ap.parse_args()
P = os.path.abspath(a.project)
cfg = json.load(open(os.path.join(P, "audio", "sfx_cues.json")))
DUR = a.duration or cfg.get("duration")
if not DUR and os.path.exists(os.path.join(P, "audio", "timing.json")):
    DUR = json.load(open(os.path.join(P, "audio", "timing.json")))["duration"]
if not DUR:
    sys.exit("set \"duration\" in audio/sfx_cues.json (or pass --duration)")
N = int(DUR * L.SR)

cues = list(cfg.get("cues", []))
kinds = dict(KIND)
kinds.update({k: tuple(v) for k, v in cfg.get("event_kinds", {}).items()})
slots = cfg.get("slots", {})
unknown = []
for path in sorted(glob.glob(os.path.join(P, "compositions", "**", "*.motion.json"), recursive=True)):
    sid = os.path.basename(path).replace(".motion.json", "")
    if sid not in slots:
        continue
    for i, ev in enumerate(json.load(open(path)).get("events", [])):
        k = ev.get("kind")
        if k not in kinds:
            unknown.append(f"{sid}:{k}")
            continue
        fx, g, args = kinds[k]
        args = dict(args)
        if fx in SEEDED:
            args["seed"] = sum(map(ord, sid)) * 100 + i
        cues.append({"t": slots[sid] + float(ev["t"]), "fx": fx, "gain_db": g + float(ev.get("gain_db", 0)),
                     "label": f"{sid} {ev.get('note', k)}", "args": args, "bus": ev.get("bus", "sfx")})

buses, cache, rows = {}, {}, []
for i, c in enumerate(sorted(cues, key=lambda c: c["t"])):
    if c["fx"] not in L.GENERATORS:
        unknown.append(c["fx"])
        continue
    args = dict(c.get("args", {}))
    if c["fx"] in SEEDED:
        args.setdefault("seed", 1000 + i)
    key = (c["fx"], json.dumps(args, sort_keys=True))
    if key not in cache:
        cache[key] = L.GENERATORS[c["fx"]](**args).astype(np.float64)
    snd = cache[key]
    if c.get("align") == "end":
        start = int(c["t"] * L.SR) - len(snd)
    elif c.get("peak") and c["fx"] == "whoosh":
        start = int((c["t"] - 0.55 * args.get("dur", 0.6)) * L.SR)  # whoosh() peaks at 55% of its length
    else:
        start = int(c["t"] * L.SR)
    bus = buses.setdefault(c.get("bus", "sfx"), np.zeros((N + L.SR * 6, 2)))
    s0 = max(0, start)
    seg = snd[s0 - start :]
    end = min(len(bus), s0 + len(seg))
    if end > s0:
        bus[s0:end] += seg[: end - s0] * 10 ** (c.get("gain_db", 0) / 20)
    rows.append((c["t"], c["fx"], c.get("gain_db", 0), c.get("align", "peak" if c.get("peak") else "start"), c.get("bus", "sfx"), c.get("label", "")))


def write(path, st):
    pcm = (np.clip(st, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(L.SR)
        w.writeframes(pcm.tobytes())


out_dir = os.path.join(P, "assets", "audio")
os.makedirs(out_dir, exist_ok=True)
f = int(0.01 * L.SR)
for name, bus in buses.items():
    bus = np.tanh(bus[:N] * 1.1) / np.tanh(1.1)  # gentle glue: soft clip, then peak-normalise to -3 dBFS
    peak = np.max(np.abs(bus))
    bus = bus / peak * 10 ** (-3 / 20) if peak > 0 else bus
    bus[:f] *= np.linspace(0, 1, f)[:, None]
    bus[-f:] *= np.linspace(1, 0, f)[:, None]
    write(os.path.join(out_dir, f"{name}.wav"), bus)

if cfg.get("room_env"):
    room = L.room_tone(DUR, seed=19).astype(np.float64)[:N]
    pts = cfg["room_env"]
    env = np.interp(np.arange(N) / L.SR, [p[0] for p in pts], [p[1] for p in pts])
    write(os.path.join(out_dir, "room.wav"), room * env[:, None] * 0.9)

with open(os.path.join(P, "audio", "sfx_cuesheet.md"), "w") as fh:
    fh.write("| time (s) | effect | gain dB | align | bus | sits under |\n|---:|---|---:|---|---|---|\n")
    for t, fx, gdb, al, bus, label in rows:
        fh.write(f"| {t:.3f} | {fx} | {gdb} | {al} | {bus} | {label} |\n")
print(f"{len(rows)} cues -> {', '.join(f'assets/audio/{b}.wav' for b in buses)}{' + room.wav' if cfg.get('room_env') else ''} ({DUR}s); cue sheet audio/sfx_cuesheet.md")
if unknown:
    print("skipped unknown kinds/effects:", ", ".join(sorted(set(unknown))[:12]))
