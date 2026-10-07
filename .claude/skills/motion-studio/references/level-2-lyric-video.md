# Level 2: the kinetic lyric music video (original song, made locally)

Claude is the songwriter, animator, sound designer and render engineer. It writes an original song,
generates it on this computer with ACE-Step 1.5, picks the best take without listening, finds the exact
moment every word is sung, and drives every animation from those times.

**Example:** `examples/prompts/level-2-lyric-video.txt` → "Sixty Frames Out": 35.6 s, 140 BPM hyperpop/DnB,
12 takes generated, take seed131 chosen. It has 9 visual worlds (particle typography, liquid chrome, a
film-frame window, a hush, a 3D chrome canyon on the drop, a kaleidoscope, a wall of sixty frames, render
passes, the outro). Every word lands on its sung onset and every cut on a downbeat.

## Brief template

```
You are the director, songwriter, animator, sound designer and render engineer for a lyric music video
made entirely in code. Work autonomously: make every decision yourself, say what you chose in one line,
keep going until a verified MP4 exists.
THE FILM: a <30-40> s, <energy> kinetic lyric video for an original song about <topic>, where every word,
cut and hit is locked to the vocal. <Maximal / restrained>, but clean, readable and intentional.
THE SONG: original, catchy, about <topic> (hook: "<hook line>"). Short punchy lines, a chantable hook
repeated at least 3 times, one big chorus/drop. <genre>, <BPM>, <vocal>. [intro] [verse] [chorus] [bridge] [outro].
LOOK: one bold art direction (<name it>) with at least 3 distinct visual "worlds" that switch at section
changes. No visual idea is used twice. Do NOT use: <ban list>.
TECHNIQUES to reach for: real 3D (Three.js chrome/glass type, a camera flying through a world of lyrics),
shader backgrounds (liquid, displacement, kaleidoscope), particle typography that assembles and explodes,
mask and shape reveals, grid multiplication, SVG morphs, speed ramps, audio-reactive elements driven by
the measured track. Search the registry before hand-building any named effect.
MUSIC: local and free with motion-studio's pipeline (≥4 takes, rank on the vocal stem, word timing).
SFX: synthesized at the exact cut/hit times, mixed under the music.
GATES: check passes with 0 errors; critique loop until every scene is 8+/10 (max 3 rounds); the MP4 has
audio, in sync. DELIVER: MP4, contact sheet, lyrics, chosen take + why, all take paths, timing.json.
```

## Pipeline

1. `bash SKILL/scripts/new_project.sh videos/<name> 2`. Write BRIEF.md, frame.md and STORYBOARD.md (worlds per section).
2. **Write the song** into `audio/song.json` (see `references/music.md`: caption, lyrics, bpm, duration = target + 2 s, seeds).
3. `bash SKILL/scripts/music/run_music.sh <project>`: 4 takes (waits in line if another chat is generating).
4. `bash SKILL/scripts/music/stems.sh <project> seed11 seed23 seed47 seed89`: vocal stems + transcripts for EVERY take.
5. `SKILL/scripts/py SKILL/scripts/music/rank_takes.py <project>`. Pick the top take unless the numbers show
   a problem (no drop, band thins out, tempo drift). If the best lyric match is under ~0.6, rewrite the caption
   (stress "every word crisp and intelligible") or simplify the lyrics, and run 4 NEW seeds.
6. `SKILL/scripts/py SKILL/scripts/music/timing.py <project> --take <best>`. Read the report: check every `*`
   word (subst / token-fill / onset-fill) against the energy and phrase gaps, and note "unsung" lines (show
   them as a title over the instrumental tail, or drop them).
7. `bash SKILL/scripts/music/trim.sh audio/takes/<best>.wav <duration from timing.json> assets/audio/song.wav`.
   The video is exactly that long.
8. Re-time STORYBOARD.md to `timing.json`: scene changes on downbeats (or section starts), **the drop gets the
   biggest visual moment**, and every lyric word appears on its `t`.
9. Build the worlds (/general-video, sub-compositions). Put `<script src="assets/js/timing.js"></script>` in
   index.html's head. Scenes read `window.TIMING` (see "Driving animation from timing" below).
10. SFX (`references/sound-design.md`): whooshes peaking on cuts, impacts on slams, a riser ending on the drop,
    glitch ticks, sparkles. Mix under the song with /hyperframes-audio.
11. Gates: check → critique loop (axes: composition, motion, typography, **lyric sync**, polish) → render → `av_check.py --expect <drop>`.

## Driving animation from timing

```js
// inside a scene whose host starts at SCENE_START (global seconds)
var T = window.TIMING, SCENE_START = 15.226;
T.words.filter(function (w) { return w.t >= SCENE_START && w.t < SCENE_START + 5.1; })
  .forEach(function (w, i) {
    tl.fromTo("#w" + i, { yPercent: 110 }, { yPercent: 0, duration: 0.22, ease: "expo.out" }, w.t - SCENE_START);
  });
// audio-reactive: one clock tween from 0, read envelopes by frame (seek-safe; never tl.call)
var clock = { t: 0 };
tl.to(clock, { t: 5.1, duration: 5.1, ease: "none", onUpdate: function () {
  var f = Math.min(T.env.kick.length - 1, Math.floor((SCENE_START + clock.t) * T.env_fps));
  stage.style.setProperty("--kick", T.env.kick[f]);   // scale/brightness pulse on the kick
} }, 0);
```
`TIMING.downbeats` gives cut points, `TIMING.drop` the drop, `TIMING.sections` the worlds, `TIMING.drum_hits` the
kick/snare onsets for punches, and `TIMING.env.vocal` the glow on sung syllables.

## What made the example work

- **Lyrics as material.** Every world is a different "state of matter" of the same words: signal → liquid → film → solid → render → light.
- **Section changes = world changes.** The a cappella break before the drop is a deliberate hush (near-empty frame), so the drop hits harder.
- **Ban list.** It banned every palette, font and technique of the earlier videos, which forced new ideas.
- **Typography register switch.** One wide display face for the singer and one mono for "the machine" (HUD, counters, timecode).
