Install the free "motion-studio" Claude Code skill for me and make sure it works.

1. FIND IT. I downloaded it (probably from Skool or Google Drive). Look in ~/Downloads first, then ~/Desktop, for anything named like "motion-studio" or "Motion Graphics Skill". It may be a .zip, a folder, or a .zip inside another .zip. Unzip into a temporary folder as needed until you find the folder whose SKILL.md starts with "name: motion-studio". If you can't find it, ask me where it is.

2. INSTALL IT to ~/.claude/skills/motion-studio/ (on Windows: %USERPROFILE%\.claude\skills\motion-studio). If that folder already exists, rename the old one to motion-studio.backup-<today's date> first. Copy the whole folder (SKILL.md, README.md, references/, scripts/, templates/, examples/), then run: chmod +x ~/.claude/skills/motion-studio/scripts/*.sh ~/.claude/skills/motion-studio/scripts/*/*.sh ~/.claude/skills/motion-studio/scripts/py

3. SET UP THE CORE: run  bash ~/.claude/skills/motion-studio/scripts/setup.sh
   It checks Node.js 22+, ffmpeg and Python, installs numpy privately if needed, downloads the free renderer's headless Chrome, and installs the free HyperFrames skills. If anything is missing, install it the free, official way for my computer (Node.js LTS from nodejs.org or Homebrew; ffmpeg with Homebrew, winget or apt; Python from python.org). Ask me before any step that needs my password. Re-run setup.sh until it prints "All set".

4. PROVE IT WORKS: run  bash ~/.claude/skills/motion-studio/scripts/selftest.sh
   It synthesizes sound effects, renders a 3-second clip and checks the audio is in sync. Open ~/motion-studio/_selftest/renders/selftest.mp4 for me.

5. THE MUSIC STUDIO (for lyric videos and story films). Check my free disk space first. It needs about 15 GB to install (the free ACE-Step 1.5 music model is ~11 GB), and about 10 GB must stay free while it makes music (otherwise a 16 GB computer can run out of memory and restart). Tell me how much space I have and ASK ME before installing it. If there isn't enough room, skip this step and tell me what to free up. If I say yes, run:
   bash ~/.claude/skills/motion-studio/scripts/setup.sh --music
   (it takes a while: it downloads the model once), then prove it works with:
   bash ~/.claude/skills/motion-studio/scripts/setup.sh --music-test
   If I already have ACE-Step-1.5 somewhere, reuse it with --acestep-dir <path> instead of downloading it again.

6. TELL ME in plain words: what you installed and where, that it cost $0, whether the music studio is installed, and 3 things I can ask you now: a level 1 showreel, a level 2 lyric music video with an original song, and a level 3 story film. Remind me to start a new Claude Code session so the skill loads.

Rules: keep everything free (no paid APIs, credits, accounts or sign-ups). Don't change anything outside ~/.claude/skills/ (motion-studio plus the free HyperFrames skills), ~/motion-studio, ~/motion-studio-tools and the free tools listed above.
