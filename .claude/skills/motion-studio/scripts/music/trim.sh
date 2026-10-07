#!/usr/bin/env bash
# Trim a take to its MUSICAL end (from rank_takes.py / timing.py "musical_end") with a short fade.
#
#   trim.sh <take.wav> <end-seconds> <out.wav> [fade-seconds=0.6]
#
# The video is then made exactly <end-seconds> long.
set -eu
in="${1:?usage: trim.sh <take.wav> <end-seconds> <out.wav> [fade]}"
end="${2:?end seconds}"
out="${3:?out.wav}"
fade="${4:-0.6}"
mkdir -p "$(dirname "$out")"
fs="$(awk -v e="$end" -v f="$fade" 'BEGIN { s = e - f; if (s < 0) s = 0; printf "%.3f", s }')"
ffmpeg -loglevel error -y -i "$in" -t "$end" -af "afade=t=in:st=0:d=0.01,afade=t=out:st=$fs:d=$fade" -ar 48000 -ac 2 -c:a pcm_s16le "$out"
echo "$out: $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out") s"
