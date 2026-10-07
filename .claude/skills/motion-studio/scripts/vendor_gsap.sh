#!/usr/bin/env bash
# Make a project independent of the GSAP CDN: download GSAP from the npm registry into
# <project>/assets/vendor/gsap.min.js and point every <script src=".../gsap.min.js"> in the project's HTML at it.
# Use it where the renderer's Chrome can't reach cdn.jsdelivr.net (sandboxes, CI, cloud sessions with a network
# allow-list). Safe to re-run.
#
#   vendor_gsap.sh <project-dir> [gsap-version]      default version: 3.14.2 (what the templates load)
set -eu
dir="${1:?usage: vendor_gsap.sh <project-dir> [gsap-version]}"
ver="${2:-3.14.2}"
P="$(cd "$dir" && pwd)"
out="$P/assets/vendor/gsap.min.js"
if [ ! -s "$out" ]; then
  tmp="$(mktemp -d)"
  (cd "$tmp" && npm pack --silent "gsap@$ver" >/dev/null && tar -xzf gsap-*.tgz package/dist/gsap.min.js)
  mkdir -p "$(dirname "$out")"
  cp "$tmp/package/dist/gsap.min.js" "$out"
  rm -rf "$tmp"
fi
find "$P" -name '*.html' -not -path '*/node_modules/*' -not -path '*/renders/*' | while read -r f; do
  rel="$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], os.path.dirname(sys.argv[2])))' "$out" "$f")"
  sed -i.bak -E "s#src=\"https?://[^\"]*/gsap(@[^/\"]*)?/dist/gsap\.min\.js\"#src=\"$rel\"#g" "$f" && rm -f "$f.bak"
done
echo "gsap $ver vendored: $out"
