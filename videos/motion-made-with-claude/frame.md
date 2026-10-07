# frame.md — design truth

## Concept
A single acid-lime dot is the only actor. Every phase hands over at the dot's extreme pose:
the squash becomes the launch, the arrival becomes the ring, the ring becomes the mask,
MOTION's collapse becomes a bar, the bar's retreat becomes the wipe, and the dot finally rests as the period.

## Palette (never pure #000 / #fff)
| hex | role |
|---|---|
| #16161A | charcoal ground (full bleed) |
| #1F1F24 | faint floor line / ring shadow tone |
| #F1ECE2 | warm white — display type |
| #9C978D | warm grey — corner chrome labels (AA on ground) |
| #C8FF2E | acid lime — THE accent, only ever the dot / its trail / its ring / its bar |

## Type
- Archivo Black — display (MOTION ~430 px, lockup ~150 px), tight tracking.
- IBM Plex Mono 500 — chrome labels 22 px, uppercase, +0.12em tracking.

## Motion rules
- Silent grid: key poses on 0.25 s multiples (0.50 land, 1.75 arrive, 2.75 reveal open, 3.25 crush, 3.50 period, 3.75 settle).
- Speed ramps INTO hits (power3/4.in), settle out of them (expo.out / elastic with low amplitude).
- Squash and stretch on every contact; stretch along velocity while travelling.
- Stillness: final lockup holds ≥ 1.2 s.

## Transitions
Dot → path (launch from squash) · trail swallowed by the dot · dot hollows to a ring = circular mask reveal ·
vertical crush to a bar · bar retracts as a wipe · bar rounds into the period. No crossfades.

## Do NOT use
- centred text that simply fades in; repeated opacity fades; slide-in-from-side transitions
- purple/blue gradients, glassmorphism cards, glow blooms, Inter / Helvetica
- more than one accent colour; lime as a full-screen fill
- pastel daylight + Instrument Serif + violet (the Level 1 example's look)
