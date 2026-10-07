# BRIEF

workflow: general-video
flow: automation
storyboard: no
mode: autonomous
level: 1 (motion-studio showreel / sting)
destination: desktop / YouTube → aspect 1920x1080
fps: 60
length: 5.0 s exactly (300 frames)
language: English (on-screen type only)
narration: no · music: no · sfx: a few synthesized cues (numpy, local)

message: One lime dot carries every move — it lands, draws, opens into MOTION, and signs off as the full stop of "MADE WITH CLAUDE."

Director's brief (motion-studio Level 1 template):
Make a dynamic 5-second motion graphics sting that proves one object can carry a whole piece.
No music: the motion carries the rhythm on a silent 0.25 s grid.
LOOK: charcoal ground #16161A, warm white type #F1ECE2, muted warm grey labels #9C978D, ONE acid-lime accent #C8FF2E.
Archivo Black for display, IBM Plex Mono for small labels, no texture. Do NOT use: see frame.md ban list.
THROUGH-LINE: one continuous shot where the lime dot never cuts: it lands with squash and stretch (01),
draws a smooth S-path and swallows its own trail (02), hollows into a ring that masks open oversized MOTION (03),
crushes MOTION into a lime bar that retracts as a wipe and lands as the full stop of MADE WITH CLAUDE. (04).
CHROME: corner technique label 01/04 … 04/04, timecode, progress bar.
FORMAT: HyperFrames, 1920x1080 at 60 fps, deterministic and seek-safe.
GATES: snapshot every phase, fix overlaps / weak transitions, `npx hyperframes check` 0 errors, render, verify 300 frames + SFX sync.
