# Music: free, local, timed

ACE-Step 1.5 (MIT) runs on this computer: Apple Silicon (MPS + MLX), NVIDIA (CUDA), or CPU (slow).
The turbo model makes a 40 s take in well under a minute on an M-series Mac once loaded. Disk: about 11 GB
of models + its Python environment. Installed by `setup.sh --music` (path saved in `SKILL/.acestep`).

## audio/song.json

| field | meaning |
|---|---|
| `mode` | `"song"` (vocals; ranked on lyrics) or `"score"` (instrumental story score; ranked on the arc) |
| `caption` | the sound, most important words first: genre, BPM, vocal (or "instrumental"), instruments, production, energy arc in time order. The examples are 450-900 characters. |
| `lyrics` | `[section]` tags + lines. Score mode: tags with directions (`[Intro - solo soft piano, no drums]`), optionally a short wordless chant at the drop |
| `instrumental` | `true` forces no vocals |
| `bpm`, `timesignature` | the requested tempo (also the hint for the beat tracker) |
| `duration` | target length + 2-4 s (takes often end early; trim to the musical end later) |
| `target_duration` | the length you need; takes whose music ends before it are penalised |
| `seeds` | 4 per round; use NEW seeds for a new round |
| `drop_window`, `arc` | score mode: where the drop should be, and the target loudness curve `[[t, 0..1], ...]` |
| `fps` | envelope rate in timing.json (30, or 60 for 60 fps pieces) |
| `lm` | `acestep-5Hz-lm-0.6B` (fits 16 GB, the default) or `acestep-5Hz-lm-1.7B` (32 GB+) |

### Writing a song that sings back right
- Short lines, simple words, a hook repeated 3+ times, one idea per line. Tongue-twisters come back as mush.
- Ask for clarity in the caption: "clear lead vocal, every word crisp and intelligible".
- Heavily processed sections (vocoder, chops) won't transcribe. That's fine: timing.py fills them from onsets and flags them.
- Score mode: describe contrast explicitly ("the first fifteen seconds are only a soft, lonely solo piano: no drums,
  no bass, very quiet" … "a breakdown: everything drops out except a riser" … "then the drop hits at full power").
  Models default to "loud all the way through" unless told otherwise.

## The commands

```bash
bash   SKILL/scripts/music/run_music.sh <project>                    # 4 takes → audio/takes/seed*.wav (waits for the lock)
bash   SKILL/scripts/music/stems.sh <project> seed11 seed23 ...      # song mode: stems + vocal-stem transcript per take
SKILL/scripts/py SKILL/scripts/music/rank_takes.py <project>         # ranking table + audio/takes/ranking.json
SKILL/scripts/py SKILL/scripts/music/timing.py <project> --take seed23   # audio/timing.json + assets/js/timing.js
bash   SKILL/scripts/music/trim.sh <project>/audio/takes/seed23.wav <duration> <project>/assets/audio/song.wav
```
Run `run_music.sh` in the background for long rounds and poll the log (`audio/gen.log`). Use absolute paths in
background commands.

## Why it's built this way (lessons that cost a debug round each)

- **Two processes.** On 16 GB, loading the model AND decoding audio in one process gets killed (exit 137). `gen_song.py`
  saves latents, and `decode_latents.py` decodes them in a fresh process with only the VAE loaded. The bf16 patch halves
  the model's memory on Apple GPUs.
- **Keep ~10 GB of disk free while generating.** Loading the model pushes a 16 GB machine into swap. With too little free
  disk macOS can't grow swap and the whole computer restarts (this happened twice, at 0.3 GB and 4 GB free). run_music.sh
  refuses to start below 10 GB free (`MOTION_STUDIO_FORCE=1` overrides it on 32 GB+ machines). Check song.json without
  loading anything: `cd <ACE-Step> && MOTION_STUDIO_DRY_RUN=1 uv run python SKILL/scripts/music/gen_song.py <project>`.
- **One music job per machine.** Two generations at once run out of memory. `run_music.sh` takes a lock in
  `~/.motion-studio/acestep.lock` (stale locks from dead processes are cleared automatically), so parallel chats wait in line.
- **Placeholder WAVs.** ACE-Step writes a silent UUID-named WAV per take. run_music.sh deletes them.
- **Rank on the vocal stem.** Full-mix transcription misranks takes (the music drowns the words).
- **Check the musical end.** One take scored 0.83 on lyrics but its music stopped at 29 s of 38. rank_takes.py
  reports `musical_end` (still audible) and `sustain_end` (band still really playing) and penalises early endings.
- **Recognisers mishear sung words** ("vibe" → "eye", "render" → "Brenda", "type it out, hit enter" → "something else
  should insert"). timing.py aligns the lyric sheet to what was heard **in order**, so misheard words keep their time.
  Unheard lines are mapped onto the leftover tokens or the vocal onsets, phrase by phrase, and flagged with `*`.
- **The drop decides the downbeat.** Kick-based downbeat guessing gets breakbeats wrong by two beats. timing.py anchors
  the bar on the drop (the sharpest rise into the loudest sustained section).
- **ACE-Step doesn't hit the requested BPM exactly** (140 → 139.7-140.0). Always use the measured grid.
- Don't download other models or edit ACE-Step's code beyond the shipped patch.

## Can't run the music model?

Not enough disk, or an old machine: use music the user owns (any WAV/MP3). Copy it to `audio/takes/user.wav`, write a
song.json with the lyrics (if any) and the bpm, then run stems.sh (needs the music studio for demucs; without it, skip
stems and time the cuts from the beat grid only) and `timing.py --take user`.
