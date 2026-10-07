# Motion Studio: a free Claude Code skill

Everything behind three motion-graphics videos made with Claude, packaged so you don't need to write a
10,000-character prompt:

1. **Showreel** (no music): one simple prompt with a real art direction. 16 s, 60 fps, 7 techniques.
2. **Lyric music video**: Claude writes an original song, makes it ON YOUR COMPUTER, picks the best take,
   finds the exact moment every word is sung, and animates to it. The sound effects are made with code.
3. **Story film**: a director's brief, a score with a drop, hundreds of synthesized sound effects, and a
   critique loop where Claude grades every shot and fixes it until each one is 8/10 or better.

## Cost: $0

| piece | what it is | price |
|---|---|---|
| HyperFrames + its skills | open-source HTML → video renderer (`npx hyperframes`) | free |
| ACE-Step 1.5 | open-source music model (MIT) that runs locally | free |
| demucs, Parakeet / whisper | vocal separation and word timing, local | free |
| Sound effects | 18 effects synthesized with numpy (no downloads) | free |
| Node.js, ffmpeg, Python | standard tools | free |

No API keys, credits, subscriptions or sign-ups on top of Claude.
**Disk:** the music model needs about **11 GB** (plus its Python environment), so check you have ~15 GB free
before installing the music part. Keep ~10 GB free while it makes music: on a 16 GB computer it swaps hard, and
with a full disk the computer can restart. Level 1 works without it.

## Install

Paste the prompt from **INSTALL-PROMPT.md** into Claude Code. Claude finds the zip, installs the skill,
sets up the free tools, and renders a quick test.

By hand: copy this folder to `~/.claude/skills/motion-studio/`, then run
`bash ~/.claude/skills/motion-studio/scripts/setup.sh` (and `--music` for levels 2-3).

## Use

Just ask:
- "Make me a 15-second showreel that shows off what you can do. Pastel, one accent colour, no music." (level 1)
- "Make a lyric music video for an original song about my coffee shop opening. Make it go crazy." (level 2)
- "Make a 60-second story film about a nurse's night shift, with a score and full sound design." (level 3)

Each video gets its own project folder with `renders/<name>.mp4`, a contact sheet, the music takes, the
timing file and the sound-effect cue sheet.

## What's inside

```
SKILL.md                    the workflow Claude follows (levels, brief, ban list, gates)
references/                 level guides, music, sound design, critique loop, lessons, art direction
examples/prompts/           the three real prompts the example videos were made from
scripts/setup.sh            installs / checks the free toolchain (--music for the music studio)
scripts/music/              ACE-Step generation, stems, take ranking, beat + lyric timing, trimming
scripts/sfx/                the numpy sound-effect library + cue builder
scripts/qa/                 A/V sync check, contact sheets
templates/                  song / score / cue templates, a self-test clip
```

Third-party licences: see LICENSES.md.
