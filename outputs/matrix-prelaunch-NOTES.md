# Matrix Finance — 30 s prelaunch film · delivery note

**Files**
- `outputs/matrix-prelaunch-30s.mp4` — H.264 High, yuv420p, 1920×1080, 30 fps, **900 frames, 30.000 s**, AAC 48 kHz stereo
  (−21.6 LUFS integrated, −1.7 dBFS true peak).
- `outputs/matrix-prelaunch-contact.jpg` — 16 frames from the final MP4 (times labelled).
- `outputs/matrix-prelaunch-storyboard.md` — final timed storyboard, as rendered.
- Editable source: `videos/matrix-prelaunch/` (HyperFrames project; see "Re-render" below).

## What is live footage and what is the planned app

| Time | Visual | Source |
|---|---|---|
| 0.0–9.5 | Holding fragments, market module, grid, hero lines | **Motion graphics.** Values and copy are the homepage's *illustrative* concept data (45/30/25, "Sideways market", Flat / Elevated / Mixed). Hero copy is the matrix.finance headline verbatim. |
| 7.5, 25.5–30 | Matrix mark | **Official asset**, `https://matrix.finance/matrix-mark.svg` (identical file on strategies.matrix.finance), unmodified. |
| 9.5–19.5 | Portfolio / Market analyzer / Strategies panels | **Planned app — product concept, not footage.** Rebuilt in HTML from the homepage concept strip ("Product concept · Illustrative data"; "All capabilities above are planned and in development, not yet available."). On screen the whole time: "PRODUCT CONCEPT · IN DEVELOPMENT" + "ILLUSTRATIVE DATA". |
| 19.5–25.5 | Browser window | **Live Strategy Archive.** Real captures of strategies.matrix.finance taken on 2026-10-07 by real clicks in Chromium: Home → ENTER THE ARCHIVE → Sideways → High-Volatility Chop → (all assets, CONTINUE) → Capital Preservation → 4 records → OPEN RECORD → STRATEGY_011 "Stablecoin Yield Rotation" → Risk. The cursor movement, page cuts and zooms are edited; the screens and click targets are real (`videos/matrix-prelaunch/assets/archive/archive-capture-log.json`). |
| 25.5–30 | End card | Motion graphics using the official mark, the site's "Matrix." / "Finance" wordmark styling, "Join the waitlist" and "Waitlist open" from matrix.finance. |

**Edited, so you know:** in the Archive sequence the intermediate Phase, Assets and Objective pages were clicked during capture
but are cut from the film; the Results breadcrumb (Sideways / High-volatility chop / All assets / Capital preservation) shows the
full path. Live pages carry small APY/match figures (e.g. "75%" archive match, "APY 4.7%"); they are never zoomed or featured — the
readable detail is the Risk table.

## Facts verified (twice)
Captured at 16:46–16:53 UTC and re-verified at **17:13 UTC, 7 Oct 2026**, before the delivery render: 31/31 on-screen strings found on
the live sites (`videos/matrix-prelaunch/source-capture/verify-result-2026-10-07.txt`), including "Waitlist open", "Currently in
development", the hero lines, every concept value, "Strategy Archive · Live today", "4 records retrieved.", and the Risk rows.
Not shown anywhere: "Download", "Start investing", app availability, AI agents, integrations or protocol logos, returns.

## Brand values used (from the site's CSS)
Background #070a09 · foreground #edf2ee · secondary #d7e2da · muted #8ea196 · primary #2fe58c · caution #e8b84b · lines #edf2ee12 ·
Inter + IBM Plex Mono (the site's fonts).

## Sound
Original, made locally with numpy: a 120 BPM minimal electronic rhythm (`audio/make_music.py`) and 21 synthesized effects
(`audio/sfx_cues.json` → `audio/sfx_cuesheet.md`). No paid music, voice, image or video APIs; no voiceover. Sync, measured in the MP4 by
cross-correlation against the effects stem: mark impact 7.500 s (0 ms), match cut 19.5 s (0 ms), clicks 20.5 / 21.6 / 22.7 s
(≤ 0.5 ms), whooshes and chime 0 ms. The story reads fully with the sound off.

## Final review scores (1–10)

| Section | Clarity | Composition | Typography | Motion | Pacing | Brand | Accuracy |
|---|---|---|---|---|---|---|---|
| 1 Portfolio 0–3 | 8 | 8 | 9 | 8 | 8 | 9 | 9 |
| 2 Market 3–6 | 8 | 8 | 9 | 8 | 8 | 9 | 9 |
| 3 Connection 6–9.5 | 9 | 9 | 9 | 9 | 8 | 10 | 10 |
| 4 Product concept 9.5–19.5 | 9 | 8 | 9 | 8 | 8 | 9 | 10 |
| 5 Live Archive 19.5–25.5 | 8 | 8 | 8 | 8 | 8 | 9 | 9 |
| 6 End card 25.5–30 | 9 | 9 | 9 | 8 | 9 | 10 | 10 |

Fixed during review (3 rounds on stills, 1 on the rendered MP4): stray shock lines before the impact; overlapping scattered fragments;
hero lines colliding with the concept label; a green connector line crossing the callouts; panels with empty space; previous panels
peeking behind the callouts; the step label overlapping moving panels; a mis-aimed push-in that broke the match cut; an empty first
window frame; the end-card CTA leaking as a green disc; the window collapsing away from the mark; the cursor lingering over the record.

**What remains (honest):** on a phone the Archive navigation screens (19.5–23.5) read as context, not text — the headline, the step rail
and the Risk close-up carry the information. The Risk close-up is readable for about 1.4 s. Section 3's "A clearer next move." is fully
set for about 1.3 s before the camera moves on.

## Re-render
```bash
cd videos/matrix-prelaunch
bash ../../.claude/skills/motion-studio/scripts/vendor_gsap.sh .       # local GSAP (the CDN is blocked in this cloud env)
python3 audio/make_music.py .                                          # assets/audio/music.wav
../../.claude/skills/motion-studio/scripts/py ../../.claude/skills/motion-studio/scripts/sfx/build_sfx.py .
npx hyperframes check                                                  # 0 errors
npx hyperframes render -o renders/matrix-prelaunch.mp4 --fps 30 --workers 2
```
