# The critique loop

What separates level 3 from a one-shot: Claude grades its own work and fixes it before you see it.

## Procedure (each round)

1. **Capture**: `npx hyperframes snapshot <project> --at <t1>,<t2>,...` at every scene's midpoint plus the key moments (word
   onsets, the turn, the drop, the end card). After rendering, `scripts/qa/contact_sheet.sh` gives one labelled grid.
2. **Look** at every image yourself (Read the PNGs/JPG). Don't score from memory of the code.
3. **Score** every scene 1-10 on the level's axes, in a table in your notes:
   - Level 1: composition, motion, typography, polish
   - Level 2: composition, motion, typography, lyric sync, polish
   - Level 3: story clarity, composition, motion fluidity, typography, sync with music and sound, polish
4. **Write down the 3 worst problems** (specific: "F6: the bezier label overlaps the curve at 27.4 s", not "improve F6").
5. **Fix them**, re-check, and go to the next round.
6. **Stop** when every score is 8+ or after the round limit (L1: 1, L2: 3, L3: 4). Report the final table.

Level 3 also runs the animation map and removes dead zones (stretches where nothing meaningful moves):
`node ~/.claude/skills/hyperframes-animation/scripts/animation-map.mjs <project>` (or under `~/.agents/skills/...`).

## What usually scores low (look for these first)

- Text overlapping text or a key object. Anything clipped by the frame edge.
- Something landing **off the beat** (levels 2-3): compare with `TIMING.downbeats` / word `t`.
- A lyric word on screen for less than ~0.3 s, or too small to read (keep lyric words ≥ 96 px at 1080p).
- Everything fading in the same way, or every move having the same ease and duration.
- Dead centre-stacked layouts with nothing in the corners for seconds.
- Low contrast (the check reports WCAG AA). Glow and grain eating small text.
- A world that looks like a different video (palette or fonts not from frame.md).
- No payoff for more than ~5 s (level 3 wants one every 3-5 s).
- Transitions that are plain crossfades where a match-cut or mask reveal was planned.
