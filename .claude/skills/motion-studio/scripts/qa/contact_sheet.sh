#!/usr/bin/env bash
# Contact sheet from a rendered MP4: one frame per time, tiled 4 across, labelled with the time.
#
#   contact_sheet.sh <video.mp4> <out.jpg> [t1 t2 ...]      (no times: 12 evenly spaced frames)
#
# Use scene midpoints and key moments (word onsets, the drop, the answer landing). For the critique loop
# BEFORE rendering, use `npx hyperframes snapshot <project> --at t1,t2,...` instead (no render needed).
set -eu
in="${1:?usage: contact_sheet.sh <video.mp4> <out.jpg> [t1 t2 ...]}"
out="${2:?out.jpg}"
shift 2
dur="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$in")"
if [ $# -eq 0 ]; then
  set -- $(awk -v d="$dur" 'BEGIN { for (i = 0; i < 12; i++) printf "%.2f ", d * (i + 0.5) / 12 }')
fi
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
font=""
for c in /System/Library/Fonts/Supplemental/Arial.ttf /System/Library/Fonts/Geneva.ttf /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf /usr/share/fonts/TTF/DejaVuSans.ttf /c/Windows/Fonts/arial.ttf; do
  [ -f "$c" ] && { font="$c"; break; }
done
ffmpeg -hide_banner -filters 2>/dev/null | grep -q ' drawtext ' || font=""
n=0
for t in "$@"; do
  n=$((n + 1))
  f="$(printf '%s/f%03d.png' "$tmp" "$n")"
  vf="scale=480:-2"
  if [ -n "$font" ]; then
    vf="$vf,drawtext=fontfile='$font':text='${t}s':x=10:y=h-th-10:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=6"
  fi
  ffmpeg -loglevel quiet -y -ss "$t" -i "$in" -frames:v 1 -vf "$vf" "$f" || ffmpeg -loglevel error -y -ss "$t" -i "$in" -frames:v 1 -vf "scale=480:-2" "$f"
done
cols=4
rows=$(( (n + cols - 1) / cols ))
ffmpeg -loglevel error -y -framerate 1 -i "$tmp/f%03d.png" -vf "tile=${cols}x${rows}:padding=6:color=black" -frames:v 1 -q:v 3 "$out"
echo "$out ($n frames)"
