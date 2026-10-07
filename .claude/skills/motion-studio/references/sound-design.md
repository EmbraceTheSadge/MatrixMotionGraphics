# Sound design: every effect is math

Motion graphics without sound feel like a slideshow. Sound is where it starts to feel like a real video. No downloads, no
stock sites: `scripts/sfx/sfx_lib.py` synthesizes everything with numpy (48 kHz stereo, seeded, so the same cues always
give the same audio). If the HyperFrames media-use skill is installed you may also use its free SFX pack, but the
synthesized set is enough.

## The 18 effects

| key | sound | typical use | args |
|---|---|---|---|
| `key` | keyboard click | one per typed character | `heavy` (space/enter) |
| `pop` | UI pop (chirp up) | a card/button appears | `f0`, `f1`, `dur`, `pan` |
| `blip` | tiny tone | thinking dots, small UI | `freq`, `pan` |
| `chime` | two-note notification | a message, a success | `freqs` |
| `whoosh` | swept noise pass | every cut, camera move, fly-by | `dur`, `pan_from`, `pan_to`, `f_lo`, `f_hi` |
| `impact` | low cinematic hit + tail | the line that lands, a stamp | `dur`, `f0`, `f1` |
| `boom` | huge sub boom | THE drop | `dur` |
| `subdrop` | sub-bass drop | under impacts | `dur` |
| `glitch` | bit-crushed crunch | slams, errors, the overwhelm | `dur`, `pan` |
| `error` | error buzz | "render failed" | `dur` |
| `riser` | noise + tone rise | INTO a hit (`align: end`) | `dur`, `f0`, `f1` |
| `swell` | reverse swell | INTO a hit (`align: end`) | `dur`, `freq` |
| `tapestop` | pitch collapsing | time freezes | `dur` |
| `paper` | paper movement | pages, cards | `dur` |
| `tick` | clock/counter tick | counters, cut points | `freq` |
| `snap` | magnetic snap | clips landing on a timeline | |
| `shutter` | camera shutter | frames rendering | |
| `shimmer` | airy sparkle bed | reveals, titles, daylight | `dur`, `base` |

Plus `room_tone` (a quiet room bed) through `room_env` keyframes. Use it in the quiet moments and silence it under the music.

## audio/sfx_cues.json → stems

```json
{"duration": 68.5,
 "room_env": [[0, 0.9], [16.6, 0.25], [18.4, 0], [59.8, 0], [62, 0.55], [68.5, 0.6]],
 "slots": {"01-hook": 0.0, "02-old-way": 6.031},
 "cues": [
   {"t": 12.031, "fx": "tapestop", "gain_db": -5, "label": "time freezes"},
   {"t": 16.031, "fx": "swell", "gain_db": -7, "align": "end", "args": {"dur": 1.4, "freq": 98}, "label": "into the answer"},
   {"t": 16.031, "fx": "impact", "gain_db": -1, "label": "THE ANSWER LANDS"},
   {"t": 18.031, "fx": "whoosh", "gain_db": -7, "peak": true, "args": {"dur": 0.75}, "label": "seam push-through"},
   {"t": 50.031, "fx": "riser", "gain_db": -4, "align": "end", "args": {"dur": 5.6}, "label": "into the drop"},
   {"t": 50.031, "fx": "boom", "gain_db": 0, "label": "DROP"}]}
```
`SKILL/scripts/py SKILL/scripts/sfx/build_sfx.py <project>` → `assets/audio/sfx.wav` (+ one stem per `"bus"` if you
group cues, e.g. `"bus": "ui"`), `room.wav`, and `audio/sfx_cuesheet.md` (deliver this).

**Scene events** (level 3): every scene worker writes `compositions/frames/<id>.motion.json`
`{"events": [{"t": 1.25, "kind": "key", "note": "typed H"}, ...]}` with local times. With `"slots"` mapping scene id →
global start, build_sfx.py turns each event into a cue (kinds: key, key_heavy, backspace, pop, land, slam, error, notify,
stamp, snap, tick, shutter, whoosh, marker, paper, glitch, blip, impact, boom, chime, shimmer; override with `"event_kinds"`).
That's how a film gets hundreds of effects that land on the exact frame.

## Placement rules

- Times come from `audio/timing.json` (downbeats, `drop`, word onsets) and the storyboard, never by ear.
- A whoosh should **peak** on the cut (`"peak": true`), not start on it. Risers and reverse swells **end** on the hit (`"align": "end"`).
- Big moments get layers: swell → impact + subdrop. The drop gets riser + swell → boom + subdrop.
- Typing: one `key` per character, `heavy` on spaces and enter. Slams: `glitch`. Counters: `tick` / `shutter`, accelerating.
- Gains: UI detail -15 to -20 dB, transitions -6 to -10 dB, hits -6 to 0 dB. Under a full band, lift montage effects
  +2 to +4 dB so they read through. Let the storyboard-level hit own its moment and drop scene events that would fight it.

## Mixing (in index.html, with /hyperframes-audio)

- Music: `<audio id="song" src="assets/audio/song.wav" data-start="0" data-duration="<len>" data-track-index="10">`.
- SFX on a group with a high-pass (leave the sub to the music) and a limiter as the ceiling, e.g.
  `<hf-audio-group id="sfx" data-fx-chain='{"version":1,"nodes":[{"type":"highpass","id":"n1","params":{"frequency":38,"q":0.707}},{"type":"limiter","id":"n2","params":{"limit":-6,"attack":3,"release":60,"level_out":0}}]}'>`
  with each SFX `<audio data-audio-group="sfx" ...>`.
- Duck the music briefly under the key hits. Optional story filter: low-pass the score during a freeze and snap it open on the turn.
- **Every `<audio>` needs an `id`.** Verify the final MP4 with `scripts/qa/av_check.py --expect <hit times>`.
