# frame.md — design truth (extracted from matrix.finance CSS, 2026-10-07)

## Palette (site CSS variables)
| hex | site token | role |
|---|---|---|
| #070a09 | --background | ground |
| #0a0e0c | --surface | panels |
| #0c100e | --card | cards |
| #111713 | --elevated | raised chips |
| rgba(237,242,238,.07) | --line (#edf2ee12) | grid lines |
| rgba(237,242,238,.09) | --border (#edf2ee17) | card borders |
| #edf2ee | --foreground | primary type |
| #d7e2da | --secondary-foreground | secondary type |
| #8ea196 | --muted-foreground | labels |
| #2fe58c | --primary | THE accent: signal, connections, CTA, the period |
| #27bf76 | --primary-dim | second bar segment |
| #e8b84b | --caution | "Sideways market", elevated volatility, DeFi segment |

## Type (site fonts)
- Inter 600/700, tight tracking (-0.03em) — display and UI.
- IBM Plex Mono 500, uppercase, +0.14em — labels, grid annotations, URLs.
- Minimums for phone viewing at 1080p: labels ≥ 26 px, callouts ≥ 84 px, UI text ≥ 26 px.

## Brand assets
- `assets/brand/matrix-mark.svg` — the official mark served at matrix.finance/matrix-mark.svg (identical on strategies.matrix.finance).
- Wordmark as on the site header: "Matrix" + green "." over "Finance" (Inter bold / medium muted).

## Grid as the motion system
96 px cells, hairlines at --line, "+" registration marks like the site. Problem = fragments float off-grid at
different depths and tilts. Answer = they accelerate, snap to cells, connect with green hairlines. Lines, masks,
camera moves and match cuts carry every transition.

## Motion rules
- Tempo 120 BPM (0.5 s beat). Section changes on beats: 3.0, 6.0, 7.5 (mark), 9.5, 13.0, 16.5, 19.5, 25.5.
- Speed ramps into hits (power3.in), expo/power4.out settles, no element simply fades onto a static page.
- Text reveals through line masks (word slots), never opacity-only.

## Do NOT use
falling code, coins, rockets, glowing trading charts, purple/blue gradients, glassmorphism, lens flares,
repeated fades, generic slide-ins, protocol logos (implied integrations), any returns/APY as a hero detail,
"Download", "Start investing".
