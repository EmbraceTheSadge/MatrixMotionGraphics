#!/usr/bin/env bash
# Start a motion-studio project: a HyperFrames project + the audio files for its level.
#
#   new_project.sh <project-dir> <level>        level: 1 (showreel, no music) | 2 (lyric music video) | 3 (story film)
#
# Level 2 gets audio/song.json (a song with vocals); level 3 gets audio/song.json in score mode (instrumental
# with a story arc); both get audio/sfx_cues.json. Fill them in, then follow SKILL.md.
set -eu
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
dir="${1:?usage: new_project.sh <project-dir> <1|2|3>}"
level="${2:?level 1, 2 or 3}"
case "$level" in 1|2|3) ;; *) echo "level must be 1, 2 or 3" >&2; exit 2 ;; esac
if [ -e "$dir/index.html" ]; then
  echo "$dir already has a project (index.html); not touching it" >&2
  exit 2
fi
parent="$(dirname "$dir")"
mkdir -p "$parent"
(cd "$parent" && npx --yes hyperframes init "$(basename "$dir")" --non-interactive --example=blank --skill=general-video >/dev/null)
P="$(cd "$dir" && pwd)"
mkdir -p "$P/audio" "$P/renders"
if [ "$level" = 2 ]; then
  cp "$SKILL_DIR/templates/song.json" "$P/audio/song.json"
elif [ "$level" = 3 ]; then
  cp "$SKILL_DIR/templates/score.json" "$P/audio/song.json"
fi
[ "$level" = 1 ] || cp "$SKILL_DIR/templates/sfx_cues.json" "$P/audio/sfx_cues.json"
echo "project: $P (level $level)"
case "$level" in
  1) echo "next: BRIEF.md + frame.md, then build (references/level-1-showreel.md)" ;;
  2) echo "next: write the song in audio/song.json, then: bash \"$SKILL_DIR/scripts/music/run_music.sh\" \"$P\"  (references/level-2-lyric-video.md)" ;;
  3) echo "next: beat sheet + score caption in audio/song.json, then: bash \"$SKILL_DIR/scripts/music/run_music.sh\" \"$P\"  (references/level-3-story-film.md)" ;;
esac
