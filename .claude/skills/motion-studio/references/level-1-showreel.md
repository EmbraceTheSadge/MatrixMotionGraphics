# Level 1: the showreel (no music)

The viral sentence with a real art direction behind it. It's great for testing a setup and for logo
stings, intros and portfolio pieces. Its weakness: hundreds of people use the same sentence, so add an
idea and a look that are yours.

**Example:** `examples/prompts/level-1-showreel.txt`. It produced a 16 s, 60 fps piece: soft pastel daylight,
Instrument Serif italic + JetBrains Mono, one electric-violet shape that never cuts. It lands as the full
stop of "motion." with squash and stretch, becomes a button a cursor presses, opens into a card with a
masked word slot, splits into 12 tiles that flip in a 3D wave, falls into a springy bar chart whose line
melts into a wave, collapses into a dot that bursts into a 3D particle sphere, and the particles spell the
wordmark with the dot dropping in as its full stop. Each technique is labelled in the corner (01/07 …
07/07) with a timecode and a progress bar.

## Brief template (fill every slot yourself)

```
Make a dynamic <10-20>-second motion graphics <showreel / sting / intro> that <what it proves or says>.
No music: the motion has to carry the rhythm on its own.
LOOK: <palette: 3-5 colours with roles + ONE accent>, <display font> for display type with <label font>
for small labels, <texture: grain / paper / glass / none>. Do NOT use: <ban list, see SKILL.md §2>.
THROUGH-LINE: one continuous shot where <ONE object> never cuts: it <technique 1>, becomes <technique 2>,
... and ends as <the lockup>. (A new technique every ~2 s.)
CHROME: label each technique in a corner (01/0N <name> … 0N/0N lockup), a timecode, a progress bar.
FORMAT: HyperFrames (start with /hyperframes), <1920x1080 | 1080x1920> at 60 fps, deterministic and seek-safe.
GATES: snapshot every phase, fix anything that overlaps or lands off-beat, `npx hyperframes check` passes,
render to renders/<name>.mp4 and open it.
```

## Rules that make it look professional

- **One through-line object.** Morphing one shape through every technique reads as mastery. Seven
  unrelated clips read as a template. Hand over between techniques at the object's extremes (a squash
  becomes a button, a collapse becomes a dot).
- **A silent tempo.** No music doesn't mean no rhythm. Pick an invisible grid (for example a pulse every
  0.5 s) and land every key pose on it. Fast-in / slow-settle eases, overshoot on landings, and stillness
  between phrases.
- **A technique every ~2 s**, from a varied menu: squash and stretch, a UI micro-interaction (cursor press,
  toggle), masked kinetic type (a word slot cycling), a 3D tile flip wave, data viz (a springy bar chart →
  line → wave), SVG morph, stroke draw-on, a particle sphere or particle typography in 3D, a liquid blob, a
  depth parallax camera push, and a logo lockup.
- **60 fps** for the fluid feel. Keep the composition in one `index.html` if it's short, and use
  sub-compositions if it grows.
- **Corner chrome** (labels, timecode, progress) makes it read as a reel and fills dead corners. Keep it ≥ 20 px.
- Optional: synthesized SFX without music (`references/sound-design.md`): a soft tick per technique, a
  pop on the press, a whoosh on the burst. Still $0.

## Gates

Snapshot every phase (`npx hyperframes snapshot <dir> --at <phase midpoints>`), run the critique loop once
(`references/critique-loop.md`; axes: composition, motion, typography, polish), and pass `check` with 0 errors.
Render and open it.
