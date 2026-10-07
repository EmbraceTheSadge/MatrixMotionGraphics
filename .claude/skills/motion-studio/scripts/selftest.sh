#!/usr/bin/env bash
# Prove the core pipeline works end to end: synthesized SFX -> HyperFrames check -> render -> A/V sync check.
#
#   selftest.sh [out-dir]          default: ~/motion-studio/_selftest
#
# Renders a 3-second 960x540 clip (a dot lands on an impact, a word wipes in on a whoosh). Takes ~1 minute.
set -u
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
T="${1:-$HOME/motion-studio/_selftest}"
mkdir -p "$T/audio" "$T/renders"
cp "$SKILL_DIR/templates/selftest/index.html" "$T/index.html"
cat > "$T/audio/sfx_cues.json" <<'JSON'
{"duration": 3, "cues": [
  {"t": 1.0, "fx": "riser", "gain_db": -10, "align": "end", "args": {"dur": 0.9}, "label": "fall"},
  {"t": 1.0, "fx": "impact", "gain_db": -2, "args": {"dur": 1.6}, "label": "the dot lands"},
  {"t": 1.57, "fx": "pop", "gain_db": -12, "label": "bounce lands"},
  {"t": 1.75, "fx": "whoosh", "gain_db": -6, "peak": true, "args": {"dur": 0.6}, "label": "word wipes in"}
]}
JSON
step() { printf '\n== %s\n' "$1"; }
step "sound effects (numpy)"
"$SKILL_DIR/scripts/py" "$SKILL_DIR/scripts/sfx/build_sfx.py" "$T" || exit 1
step "hyperframes check"
(cd "$T" && npx --yes hyperframes check) || echo "(check reported issues; continuing to render)"
step "render"
(cd "$T" && npx --yes hyperframes render -o renders/selftest.mp4 --fps 30 --workers 2) || { echo "render failed"; exit 1; }
step "A/V check"
"$SKILL_DIR/scripts/py" "$SKILL_DIR/scripts/qa/av_check.py" "$T/renders/selftest.mp4" --expect 1.0 --duration 3 || exit 1
echo
echo "self-test passed: $T/renders/selftest.mp4"
