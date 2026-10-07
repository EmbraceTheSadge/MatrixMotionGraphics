"""Verify a rendered MP4: it has an audio stream, the lengths agree, and key hits are in sync.

  python av_check.py <video.mp4> [--expect 16.031 50.031 ...] [--duration 68.5]

--expect: times (s) where a hit SHOULD be (the impact under "Yes.", the drop boom). Each one reports
the nearest strong onset in the MP4's own audio and the offset. Anything over 1 frame (33 ms at 30 fps)
is out of sync: the audio element's data-start or the cue time is wrong.
"""

import argparse
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "music"))
import audiolib as A  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("--expect", type=float, nargs="*", default=[])
ap.add_argument("--duration", type=float)
a = ap.parse_args()

probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", a.video],
                                  capture_output=True, check=True).stdout)
streams = probe["streams"]
v = [s for s in streams if s["codec_type"] == "video"]
au = [s for s in streams if s["codec_type"] == "audio"]
fmt_dur = float(probe["format"]["duration"])
ok = True
if not v:
    print("FAIL: no video stream")
    ok = False
else:
    s = v[0]
    print(f"video: {s['codec_name']} {s['width']}x{s['height']} @ {s.get('avg_frame_rate')}  {float(s.get('duration', fmt_dur)):.3f}s")
if not au:
    print("FAIL: no audio stream (did the <audio> elements have ids and real src files?)")
    ok = False
else:
    s = au[0]
    print(f"audio: {s['codec_name']} {s.get('sample_rate')} Hz {s.get('channels')} ch  {float(s.get('duration', fmt_dur)):.3f}s")
if a.duration and abs(fmt_dur - a.duration) > 0.1:
    print(f"FAIL: length {fmt_dur:.3f}s, expected {a.duration}s")
    ok = False
if au:
    x = A.load(a.video)
    rms = np.sqrt(np.mean(x**2))
    print(f"audio level: {20 * np.log10(rms + 1e-9):.1f} dB RMS, peak {20 * np.log10(np.abs(x).max() + 1e-9):.1f} dBFS")
    if rms < 1e-4:
        print("FAIL: the audio track is silent")
        ok = False
    if a.expect:
        mag, fps = A.stft_mag(x, 1024, 128)
        flux = A.band_flux(mag, 30, 11000)
        for t in a.expect:
            i0, i1 = int((t - 0.15) * fps), int((t + 0.15) * fps)
            seg = flux[max(0, i0) : i1]
            if len(seg) == 0:
                print(f"  {t:.3f}s: beyond the end")
                continue
            hit = (max(0, i0) + int(np.argmax(seg))) / fps + (1024 / 2) / A.SR
            off = hit - t
            flag = "ok" if abs(off) <= 0.034 else "OUT OF SYNC"
            print(f"  hit expected {t:.3f}s -> found {hit:.3f}s ({off * 1000:+.0f} ms) {flag}")
            ok = ok and abs(off) <= 0.034
print("PASS" if ok else "CHECK THE FAILURES ABOVE")
sys.exit(0 if ok else 1)
