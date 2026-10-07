#!/usr/bin/env bash
# Generate + decode ACE-Step takes for a project, one music job per machine at a time.
#
#   run_music.sh <project-dir> [seed ...]        seeds default to song.json "seeds" (or 11 23 47 89)
#
# Reads <project>/audio/song.json, writes <project>/audio/takes/seed<N>.wav (+ .latents.pt),
# logs to <project>/audio/gen.log and decode.log. Safe to run from several chats at once: a lock
# makes them wait in line (two generations at once run a 16 GB machine out of memory).
set -u
SKILL_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
P="$(cd "${1:?usage: run_music.sh <project-dir> [seed ...]}" && pwd)"
shift
SEEDS="$*"

ACE="${MOTION_STUDIO_ACESTEP:-}"
[ -z "$ACE" ] && [ -f "$SKILL_DIR/.acestep" ] && ACE="$(cat "$SKILL_DIR/.acestep")"
if [ -z "$ACE" ] || [ ! -f "$ACE/pyproject.toml" ]; then
  echo "ACE-Step is not installed yet. Run: bash \"$SKILL_DIR/scripts/setup.sh\" --music" >&2
  exit 2
fi
[ -f "$P/audio/song.json" ] || { echo "missing $P/audio/song.json (see references/music.md)" >&2; exit 2; }
mkdir -p "$P/audio/takes"

# Loading the model pushes a 16 GB machine into swap. With too little free disk the OS can't grow swap
# and the whole computer restarts (it happened twice on a 16 GB Mac with 0.3 GB and 4 GB free).
FREE_GB="$(df -Pk "$HOME" | awk 'NR==2 {printf "%d", $4 / 1048576}')"
if [ "${FREE_GB:-0}" -lt 10 ] && [ "${MOTION_STUDIO_FORCE:-0}" != 1 ]; then
  echo "Not starting: only ${FREE_GB} GB free disk. Music generation needs ~10 GB free for swap, or the computer" >&2
  echo "can run out of memory and restart. Free up space (or MOTION_STUDIO_FORCE=1 if you have 32 GB+ of RAM)." >&2
  exit 3
fi

LOCK="$HOME/.motion-studio/acestep.lock"
mkdir -p "$HOME/.motion-studio"
echo "[$(date +%T)] waiting for the music lock"
while ! mkdir "$LOCK" 2>/dev/null; do
  holder="$(cat "$LOCK/pid" 2>/dev/null || true)"
  # stale if the owner is gone, or the pid now belongs to something else (e.g. after a restart)
  if [ -n "$holder" ] && ! ps -p "$holder" -o command= 2>/dev/null | grep -q "run_music"; then
    echo "[$(date +%T)] removing stale lock (pid $holder is not a music job)"
    rm -f "$LOCK/pid"; rmdir "$LOCK" 2>/dev/null
    continue
  fi
  if [ -z "$holder" ] && [ -n "$(find "$LOCK" -maxdepth 0 -mmin +30 2>/dev/null)" ]; then
    echo "[$(date +%T)] removing stale lock (no owner, older than 30 min)"
    rmdir "$LOCK" 2>/dev/null
    continue
  fi
  sleep 20
done
echo $$ > "$LOCK/pid"
trap 'rm -f "$LOCK/pid"; rmdir "$LOCK" 2>/dev/null' EXIT INT TERM
echo "[$(date +%T)] lock acquired; seeds: ${SEEDS:-from song.json}"

cd "$ACE" || exit 2
export TOKENIZERS_PARALLELISM=false ACESTEP_MPS_DTYPE=bfloat16 ACESTEP_SAVE_MEMORY=1 PYTHONUNBUFFERED=1
if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then export ACESTEP_LM_BACKEND="${ACESTEP_LM_BACKEND:-mlx}"; fi

# shellcheck disable=SC2086
uv run python "$SKILL_DIR/scripts/music/gen_song.py" "$P" $SEEDS > "$P/audio/gen.log" 2>&1
gen=$?
echo "[$(date +%T)] generation exit $gen (log: $P/audio/gen.log)"
uv run python "$SKILL_DIR/scripts/music/decode_latents.py" "$P" > "$P/audio/decode.log" 2>&1
dec=$?
echo "[$(date +%T)] decode exit $dec (log: $P/audio/decode.log)"
# generate_music() also writes a silent placeholder WAV per take under a UUID name
find "$P/audio/takes" -maxdepth 1 -name '*-*-*-*-*.wav' -delete 2>/dev/null

echo "takes:"
ls -1 "$P/audio/takes/"seed*.wav 2>/dev/null | sed 's/^/  /'
[ "$gen" -eq 0 ] && [ "$dec" -eq 0 ]
