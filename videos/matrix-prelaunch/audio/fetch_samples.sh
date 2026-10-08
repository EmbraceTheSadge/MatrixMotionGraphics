#!/usr/bin/env bash
# Fetch the CC0 (public-domain) instrument samples used by audio/score.py into audio/samples/ (gitignored).
#   Upright Piano KW  — FreePats, CC0 1.0   https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html
#   VSCO-2 CE strings — Versilian Studios, CC0 1.0   https://github.com/sgossner/VSCO-2-CE
# Needs: curl, and py7zr in the motion-studio venv (pip install py7zr).
set -euo pipefail
cd "$(dirname "$0")"
OUT=samples
PY=../../../.claude/skills/motion-studio/.venv/bin/python
mkdir -p "$OUT/piano" "$OUT/vsco"
if [ ! -f "$OUT/piano/.done" ]; then
  curl -sSfL -o "$OUT/kw.7z" https://freepats.zenvoid.org/Piano/UprightPianoKW/UprightPianoKW-SFZ+FLAC-20220221.7z
  "$PY" -I -c "import py7zr,sys; py7zr.SevenZipFile(sys.argv[1]).extractall(sys.argv[2])" "$OUT/kw.7z" "$OUT/kw"
  for f in "$OUT"/kw/*/samples/*.flac; do ffmpeg -loglevel error -y -i "$f" -ar 48000 -ac 2 "$OUT/piano/$(basename "${f%.flac}").wav"; done
  rm -rf "$OUT/kw" "$OUT/kw.7z"; touch "$OUT/piano/.done"
fi
while IFS= read -r p; do
  [ -z "$p" ] && continue
  dst="$OUT/vsco/$(echo "$p" | tr ' /' '__')"
  [ -f "$dst" ] && continue
  curl -sSfL -o "$dst" "https://raw.githubusercontent.com/sgossner/VSCO-2-CE/master/$(echo "$p" | sed 's/ /%20/g; s/#/%23/g')"
done < sample_list.txt
echo "samples ready: $(ls "$OUT/piano" | wc -l) piano, $(ls "$OUT/vsco" | wc -l) strings/harp"
