# MatrixMotionGraphics

Motion graphics generated with the `motion-studio` Claude Code skill (HyperFrames, $0, all local).

- `.claude/skills/motion-studio/` — the skill
- `videos/<name>/` — HyperFrames project sources (BRIEF.md, frame.md, index.html, SFX cues)
- `outputs/` — final rendered videos and contact sheets

## Re-render a project

```bash
S=.claude/skills/motion-studio
bash $S/scripts/setup.sh                          # once per machine
cd videos/motion-made-with-claude
bash ../../$S/scripts/vendor_gsap.sh .            # local GSAP (CDN may be blocked)
../../$S/scripts/py ../../$S/scripts/sfx/build_sfx.py .
npx hyperframes check
npx hyperframes render -o renders/motion-made-with-claude.mp4 --fps 60 --workers 2
```
