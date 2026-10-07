#!/usr/bin/env bash
# Split takes into vocals + instrumental (demucs htdemucs) and transcribe the vocal stem.
#
#   stems.sh <project-dir> <take> [take ...]      e.g. stems.sh videos/my-video seed11 seed23
#
# Writes <project>/audio/stems/htdemucs/<take>/{vocals.wav,no_vocals.wav,vocals16k.wav,transcript.json}
# Transcribe the VOCAL STEM, never the full mix: the music drowns the words and misranks takes.
set -u
SKILL_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
P="$(cd "${1:?usage: stems.sh <project-dir> <take> [take ...]}" && pwd)"
shift
[ $# -gt 0 ] || { echo "name at least one take (e.g. seed11)" >&2; exit 2; }
ACE="${MOTION_STUDIO_ACESTEP:-}"
[ -z "$ACE" ] && [ -f "$SKILL_DIR/.acestep" ] && ACE="$(cat "$SKILL_DIR/.acestep")"
[ -n "$ACE" ] && [ -f "$ACE/pyproject.toml" ] || { echo "ACE-Step not installed: bash \"$SKILL_DIR/scripts/setup.sh\" --music" >&2; exit 2; }

for take in "$@"; do
  take="${take%.wav}"
  src="$P/audio/takes/$take.wav"
  out="$P/audio/stems/htdemucs/$take"
  [ -f "$src" ] || { echo "missing $src" >&2; continue; }
  if [ ! -f "$out/vocals.wav" ]; then
    echo "[$(date +%T)] demucs $take"
    (cd "$ACE" && uv run python -m demucs --two-stems vocals -n htdemucs -d cpu -o "$P/audio/stems" "$src") > "$P/audio/stems.log" 2>&1 \
      || { echo "demucs failed for $take (see $P/audio/stems.log)" >&2; continue; }
  fi
  ffmpeg -loglevel error -y -i "$out/vocals.wav" -ac 1 -ar 16000 "$out/vocals16k.wav"
  if [ ! -f "$out/transcript.json" ]; then
    echo "[$(date +%T)] transcribe $take (vocal stem)"
    (cd "$out" && npx --yes hyperframes transcribe vocals16k.wav -d . --json >/dev/null 2>"$out/transcribe.log") \
      || echo "transcription failed for $take (see $out/transcribe.log)" >&2
  fi
  echo "  $take -> $out"
done
