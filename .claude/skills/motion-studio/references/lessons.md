# Lessons already learned (each one cost a debug round)

## HyperFrames composition
- **A sub-composition's inner element ids must never equal its host slot id**, or the scene silently never mounts.
- **Drive changing state from a clock tween that starts at 0** (`tl.to(clock, {t: dur, ease: "none", onUpdate})`) instead
  of `tl.call`. Seeking is then safe in both directions, and the renderer seeks.
- Deterministic only: seeded randomness (no `Math.random()`), no `Date`, no network fetches at render time.
- **Fonts:** bundled fonts render without setup (Montserrat, Oswald, League Gothic, Archivo Black, Space Mono, IBM Plex Mono,
  JetBrains Mono, Source Code Pro, …). For any other font, download the OFL woff2/ttf (Google Fonts) into `assets/fonts/`
  and declare `@font-face`.
- When index.html owns a continuous environment (sky, HUD, grain), **scenes must be transparent**: never paint an opaque
  full-bleed ground in a scene.
- Overlap scene hosts by a few tenths of a second where the incoming world reveals itself over the outgoing one.
- Render with `--workers 2`: other chats may be rendering at the same time.
- HyperFrames refuses to render with less than 1 GB free disk. Check `df -h ~` before a long render.
- Use absolute paths in background shell commands.

## Three.js / WebGL inside HyperFrames
- Vendor three.js **r147 classic builds** (sync `THREE` global; TextGeometry and Reflector still live in `examples/js`) and load
  them once in index.html's `<head>`. Loading three again per scene replaces `THREE` and drops TextGeometry.
- The `missing_three_script` lint only reads scripts inside a sub-composition's `<template>`. A truthful comment in the
  template script satisfies it: `// THREE, TextGeometry from "assets/vendor/three.min.js" (loaded by index.html)`.
- Drive every WebGL scene from one GSAP clock tween (`onUpdate` → render) with `preserveDrawingBuffer: true`.
  Scissor/viewport rendering is fine for split screens and grids.
- Variable fonts with overlapping contours (e.g. Unbounded): rasterise glyph outlines as ONE path with fill `"nonzero"`
  (per-shape even-odd punches holes). Stroked outlines need a mask of the filled glyph to hide the overlap seams.
- WebGL renders fine on Apple Silicon with the hardware GPU (ANGLE Metal).

## Music and timing
- **Never run the music model with low free disk.** A 16 GB Mac swaps hard while loading it, and with only a few GB free the
  machine restarts. Keep ~10 GB free (run_music.sh enforces it).
- See `references/music.md`: two-process generation (latents, then decode), the one-job lock, the placeholder WAVs, ranking
  on the vocal stem, the musical-end check, in-order lyric alignment, drop-anchored downbeats, and the measured grid instead
  of the requested BPM.
- Swapping takes later means re-timing everything. Pick carefully, and tell the user all the take paths up front.

## Direction
- Ban the defaults explicitly, or Claude goes back to them (centred text, a gradient, everything fading in).
- One idea per world. No visual idea used twice.
- "Make it real": when the film is about making the film, show its real script, palette, waveform and timeline.
- Run several pieces in parallel chats if you like: the music lock and `--workers 2` make that safe on one machine.
