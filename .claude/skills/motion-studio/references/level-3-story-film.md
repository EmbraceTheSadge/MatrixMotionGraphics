# Level 3: the story film (score, full sound design, critique loop)

Don't give it a task. Give it a crew and a story. Claude is director, writer, animator, composer, sound
designer and render engineer, and it grades its own shots until every one is good.

**Example:** `examples/prompts/level-3-story-film.txt` → "One Conversation", 68.5 s, 12 shots, 120 BPM score
with the drop at 50.031 s, 375 sound effects, every shot 8+/10. At 2:07 AM a solo creator with an idea and
no team types one sentence, and a film studio wakes up inside the conversation: Writer, Art Director,
Animator, Composer, Sound Designer, Editor, Render. Each role adds a colour until full daylight on the drop.

## Brief template

```
You are the director, writer, animator, composer, sound designer and render engineer for a short story
film made entirely in code. It must have real storytelling, a great score, full sound design and fluid
animation. Work autonomously; make every decision; say what you chose in one line.
THE FILM IN ONE LINE: "<title>": <who> <wants what> <and what changes>. <60-75> s.
STORY (keep the arc, improve the details):
 1 Hook (0-5 s): <one striking image + one line of text>
 2 Problem (5-12 s): <the old way piles up until the screen is overwhelmed>
 3 Turn (12-17 s): <everything freezes; one action; the answer lands with weight>
 4 Montage (17-45 s): <the change, as N "worlds" flowing into each other with no hard resets>
 5 Climax (45-55 s): <all worlds converge, on the music's drop>
 6 Resolution (last 5-8 s): <quiet; the message line; end card>
COLOUR AS STORY: <start state> → <each beat adds colour> → <full light at the climax>.
LOOK: cinematic: real depth (Three.js / CSS 3D camera moves), lighting and grade, match-cuts between
worlds, overshoot springs, motion blur on fast moves, typography with a voice. Do NOT use: <ban list>.
MUSIC: a score that follows the story (sparse → tension → lift → build → drop → resolve), mostly
instrumental; ≥4 takes ranked on the story arc; shot changes on downbeats; climax exactly on the drop.
SOUND: a full synthesized effects layer: typing, UI pops, whooshes on every camera move, a low impact when
the answer lands, glitch crunches in the overwhelm, risers and reverse swells into the drop, a deep boom,
room tone in the quiet. Narration optional (free local voice only).
GATES, in order: plan → music + timing → stills → full animation pass → polish → sound + mix → check → render.
Critique loop until every shot is 8+/10 (max 4 rounds) + animation-map dead-zone pass.
DELIVER: MP4, contact sheet, final beat sheet with timestamps, chosen take + why, all take paths, SFX list.
```

## Pipeline

1. `bash SKILL/scripts/new_project.sh videos/<name> 3`. Write BRIEF.md and frame.md (palette as a story
   progression, e.g. night `#070B16` → a role hue per world → daylight).
2. **Score** in `audio/song.json` (score mode). Describe the arc in the caption in time order and use section
   tags with directions (`[Intro - solo soft piano, no drums]`). Set `drop_window` and `arc` to your beat sheet
   (`templates/score.json` is the example). Duration = film + 2-4 s.
3. `run_music.sh` → `rank_takes.py` (arc fit, a clear drop inside the window, a quiet start, a resolving tail,
   no early ending). If nothing fits, make the caption more explicit about the quiet start and the breakdown
   before the drop, and run 4 new seeds. The example needed 2 rounds (8 takes).
4. `timing.py --take <best>` → beats, downbeats, `drop`, `novelty` (candidate section changes), loudness. **Re-time
   the beat sheet to the music**: every shot change on a downbeat, the turn/lift on the first big entry, the climax
   exactly on `drop`. `trim.sh` to the musical end, and the film is exactly that long.
5. STORYBOARD.md: one `## Frame N` block per shot with its global slot, local start, on-screen text, payoffs
   (a visual payoff every 3-5 s), transition, cited blueprint/rules, sky/colour state, and sfx. Use a **seam model**:
   montage slots carry ~0.4 s of pre-roll and post-roll so index.html can run a push-through match-cut centred
   on each seam (each world starts with its "in-object" at frame centre and ends with its "out-object" there).
6. **Make it real.** Show the film's own artefacts: the Writer world shows this film's actual script, the Art
   Director its real palette and fonts, the Composer the real score (`scripts/music/score_viz.py <score.wav> <start>
   <end> <out.json> <bpm> <first_beat>` bakes the waveform + a pitch-tracked piano roll), the Editor this film's
   real 12-shot timeline, the Render the real frame count. It's honest and it's a great payoff.
7. **Stills first:** a key frame of every shot, snapshot, critique, fix. Then the full animation pass.
8. **Parallel scene workers** (/general-video): 2-3 scenes per worker, all in one wave. Each gets its Frame block,
   frame.md, the timing slice, and the lessons. Each writes `compositions/frames/<id>.html` + `<id>.motion.json`
   with `{"events": [{"t": <local s>, "kind": "key|pop|land|slam|whoosh|tick|...", "note": "..."}]}` for every
   visual event that should make a sound.
9. index.html owns the continuous environment (sky/colour progression, HUD, grain, vignette, the seams and all
   audio). **Scenes are transparent**: they never paint an opaque full-bleed ground.
10. Sound (`references/sound-design.md`): storyboard-level cues + every scene's events → `build_sfx.py` → stems.
    Mix with /hyperframes-audio: duck the score under the key hits, a "story filter" on the score (low-pass during
    the freeze that snaps open on the turn), room tone only in the quiet parts, a master limiter.
11. Gates: check (0 errors) → critique loop (axes: story clarity, composition, motion fluidity, typography,
    sync with music and sound, polish) → `node ~/.claude/skills/hyperframes-animation/scripts/animation-map.mjs <project>`
    and remove dead zones → render → `av_check.py --expect <turn> <drop>`.

## What made the example work

- **Colour is the story.** Night → each role lights its own hue → indigo predawn → rose dawn → gold sunrise → full daylight on the drop. The corner clock runs 2:07 AM → 6:41 AM.
- **One continuous world.** Shots 1-3 are one continuous shot split in three, the montage seams are match-cuts, and there's one hard cut on the drop.
- **Sound on every event.** 36 key clicks for 36 typed characters, a glitch on every window slam, a tape-stop when time freezes, a reverse swell into the impact under "Yes.", and a 5.6 s riser into the drop boom.
- **It grades itself.** Contact sheet → scores → 3 worst problems → fix → repeat. Then it measured A/V sync on the final MP4 (the impact under "Yes." landed within 1 ms of schedule).
