#!/usr/bin/env bash
# motion-studio setup: checks (and where it safely can, installs) the free toolchain. Safe to re-run.
#
#   setup.sh                         core: Node 22+, ffmpeg, Python + numpy, HyperFrames CLI + its Chrome + its skills
#   setup.sh --music                 + the local music studio: uv, ACE-Step 1.5 (~11 GB of models), demucs, a transcriber
#   setup.sh --music --acestep-dir <path>   reuse an ACE-Step-1.5 checkout you already have
#   setup.sh --music-test            generate one short test score to prove the music studio works (~2-5 min)
#
# Everything is free and local: no API keys, credits or accounts.
set -u
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OS="$(uname -s)"
ARCH="$(uname -m)"
ACE_COMMIT="ca1e85fe9430179831e6bc6be790c332190a3866"  # the ACE-Step 1.5 revision the 3 example videos were made with
MUSIC=0
MUSIC_TEST=0
ACE_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --music) MUSIC=1 ;;
    --music-test) MUSIC_TEST=1 ;;
    --acestep-dir) ACE_DIR="$2"; shift ;;
  esac
  shift
done
problems=0
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; problems=$((problems + 1)); }
note() { printf '    %s\n' "$1"; }
free_gb() { df -Pk "${1:-$HOME}" | awk 'NR==2 {printf "%d", $4 / 1048576}'; }

echo "motion-studio setup  ($SKILL_DIR)"

# ---------------------------------------------------------------- core
if command -v node >/dev/null 2>&1; then
  major="$(node -p 'process.versions.node.split(".")[0]')"
  if [ "$major" -ge 22 ]; then ok "Node.js $(node -v)"; else bad "Node.js $(node -v) is too old (need 22+)"; note "Install the LTS from https://nodejs.org (free)."; fi
else
  bad "Node.js not found"; note "Install the LTS from https://nodejs.org (free), or: brew install node"
fi

if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
  ok "ffmpeg $(ffmpeg -version | head -1 | awk '{print $3}')"
elif [ "$OS" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
  echo "  … installing ffmpeg with Homebrew"
  brew install ffmpeg >/dev/null && ok "ffmpeg installed" || bad "brew install ffmpeg failed"
else
  bad "ffmpeg not found"
  case "$OS" in
    Darwin) note "Install Homebrew (https://brew.sh), then: brew install ffmpeg" ;;
    Linux)  note "sudo apt install ffmpeg   (or your distro's package manager)" ;;
    *)      note "winget install ffmpeg   (Windows), then reopen the terminal" ;;
  esac
fi

PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  bad "Python 3 not found"; note "Install Python 3.9+ from https://www.python.org/downloads/ (free)."
elif [ -x "$SKILL_DIR/.venv/bin/python" ] || [ -x "$SKILL_DIR/.venv/Scripts/python.exe" ]; then
  ok "Python venv with numpy ($SKILL_DIR/.venv)"
elif "$PY" -c 'import sys, numpy; assert sys.version_info >= (3, 9)' 2>/dev/null; then
  echo "$PY" > "$SKILL_DIR/.python"
  ok "Python $("$PY" -c 'import sys; print(sys.version.split()[0])') with numpy"
else
  echo "  … creating a private Python environment with numpy (~40 MB)"
  if "$PY" -m venv "$SKILL_DIR/.venv" && "$SKILL_DIR/scripts/py" -m pip install -q --upgrade pip && "$SKILL_DIR/scripts/py" -m pip install -q numpy; then
    ok "numpy installed in $SKILL_DIR/.venv"
  else
    bad "could not install numpy"; note "Try: $PY -m pip install --user numpy"
  fi
fi
chmod +x "$SKILL_DIR/scripts/py" "$SKILL_DIR"/scripts/*.sh "$SKILL_DIR"/scripts/*/*.sh 2>/dev/null

if command -v npx >/dev/null 2>&1; then
  if npx --yes hyperframes --version >/dev/null 2>&1; then
    ok "HyperFrames CLI $(npx --yes hyperframes --version 2>/dev/null | tail -1)"
    if npx --yes hyperframes browser ensure >/dev/null 2>&1; then ok "headless Chrome for rendering"; else bad "Chrome download failed"; note "Run: npx --yes hyperframes browser ensure --force"; fi
  else
    bad "could not run the HyperFrames CLI through npx (network?)"
  fi
  if [ -f "$HOME/.claude/skills/hyperframes/SKILL.md" ] || [ -f "$HOME/.agents/skills/hyperframes/SKILL.md" ]; then
    ok "HyperFrames skills (hyperframes, general-video, hyperframes-animation, ...)"
  else
    echo "  … installing the HyperFrames skills (free, open source)"
    if npx --yes hyperframes skills >/dev/null 2>&1 && { [ -f "$HOME/.claude/skills/hyperframes/SKILL.md" ] || [ -f "$HOME/.agents/skills/hyperframes/SKILL.md" ]; }; then
      ok "HyperFrames skills installed"
    else
      bad "HyperFrames skills not installed"; note "Run: npx --yes hyperframes skills"
    fi
  fi
fi

GB="$(free_gb "$HOME")"
if [ "${GB:-0}" -lt 2 ]; then bad "only ${GB} GB free disk: HyperFrames refuses to render under 1 GB, and a 1080p render wants 3+ GB"; note "Free up disk space before rendering."; fi

# ---------------------------------------------------------------- music studio
find_ace() {
  [ -n "$ACE_DIR" ] && { echo "$ACE_DIR"; return; }
  [ -f "$SKILL_DIR/.acestep" ] && { cat "$SKILL_DIR/.acestep"; return; }
  echo "$HOME/motion-studio-tools/ACE-Step-1.5"
}

if [ "$MUSIC" = 1 ]; then
  echo
  echo "music studio (ACE-Step 1.5, demucs, transcription)"
  ACE="$(find_ace)"
  if [ "$OS" = "Darwin" ] && [ "$ARCH" != "arm64" ]; then
    note "heads-up: this is an Intel Mac. ACE-Step runs on CPU here: expect several minutes per take."
  fi
  for tool in git curl; do command -v "$tool" >/dev/null 2>&1 || bad "$tool not found"; done
  if ! command -v uv >/dev/null 2>&1; then
    echo "  … installing uv (free Python project manager from astral.sh)"
    curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  fi
  if command -v uv >/dev/null 2>&1; then ok "uv $(uv --version | awk '{print $2}')"; else bad "uv install failed"; note "See https://docs.astral.sh/uv/getting-started/installation/"; fi

  if [ ! -f "$ACE/pyproject.toml" ]; then
    need=15
    GB="$(free_gb "$(dirname "$ACE")" 2>/dev/null || free_gb "$HOME")"
    if [ "${GB:-0}" -lt "$need" ]; then
      bad "only ${GB} GB free; the music studio needs ~${need} GB (11 GB of models + its Python env), then ~10 GB free to run"
      note "Free up space, or reuse an existing checkout: setup.sh --music --acestep-dir <path>"
    else
      echo "  … cloning ACE-Step 1.5 into $ACE"
      mkdir -p "$(dirname "$ACE")"
      git clone -q https://github.com/ACE-Step/ACE-Step-1.5.git "$ACE" && (cd "$ACE" && git checkout -q "$ACE_COMMIT") || bad "git clone failed"
    fi
  fi

  if [ -f "$ACE/pyproject.toml" ]; then
    echo "$ACE" > "$SKILL_DIR/.acestep"
    ok "ACE-Step checkout: $ACE"
    PATCH="$SKILL_DIR/scripts/music/acestep-mps-bf16.patch"
    if grep -q "ACESTEP_MPS_DTYPE" "$ACE/acestep/core/generation/handler/init_service_orchestrator.py" 2>/dev/null; then
      ok "16 GB Mac memory patch (bfloat16 on Apple GPUs)"
    elif (cd "$ACE" && git apply --check "$PATCH" 2>/dev/null && git apply "$PATCH"); then
      ok "16 GB Mac memory patch applied"
    else
      note "memory patch did not apply to this ACE-Step version (fine on NVIDIA / 32 GB+ machines; 16 GB Macs may run out of memory)"
    fi
    if command -v uv >/dev/null 2>&1; then
      if (cd "$ACE" && uv run python -c "import acestep" >/dev/null 2>&1); then
        ok "ACE-Step Python environment"
      else
        echo "  … installing ACE-Step's Python environment (uv sync; a few GB, several minutes)"
        (cd "$ACE" && uv sync >/dev/null 2>&1) && ok "ACE-Step Python environment" || bad "uv sync failed (run it in $ACE to see why)"
      fi
      has() { [ -n "$(find "$ACE/checkpoints/$1" -maxdepth 1 \( -name '*.safetensors' -o -name '*.bin' \) 2>/dev/null | head -1)" ]; }
      if has acestep-v15-turbo && has vae && has Qwen3-Embedding-0.6B && has acestep-5Hz-lm-1.7B; then
        ok "ACE-Step main model (turbo DiT, VAE, text encoder)"
      else
        echo "  … downloading the ACE-Step main model (~9.5 GB, free from Hugging Face; this takes a while)"
        (cd "$ACE" && uv run acestep-download >/dev/null 2>&1) && ok "main model downloaded" || bad "model download failed (run: cd \"$ACE\" && uv run acestep-download)"
      fi
      if has acestep-5Hz-lm-0.6B; then
        ok "ACE-Step 0.6B language model (the light one that fits 16 GB)"
      else
        echo "  … downloading the 0.6B language model (~1.3 GB)"
        (cd "$ACE" && uv run acestep-download --model acestep-5Hz-lm-0.6B --skip-main >/dev/null 2>&1) && ok "0.6B LM downloaded" || bad "LM download failed"
      fi
      if (cd "$ACE" && uv run python -c "import demucs" >/dev/null 2>&1); then
        ok "demucs (vocal / instrumental stem separation)"
      else
        echo "  … installing demucs into ACE-Step's environment"
        (cd "$ACE" && uv pip install -q demucs >/dev/null 2>&1) && ok "demucs installed" || bad "demucs install failed"
      fi
    fi
  fi

  if [ "$OS" = "Darwin" ] && [ "$ARCH" = "arm64" ]; then
    if [ -d "$HOME/.cache/huggingface/hub/models--mlx-community--parakeet-tdt-0.6b-v3" ] || command -v parakeet-mlx >/dev/null 2>&1; then
      ok "Parakeet transcription (word timings of sung lyrics)"
    elif [ "$(free_gb "$HOME")" -lt 4 ]; then
      bad "not enough disk for the Parakeet model (~2.5 GB)"; note "Free some space, then: npx hyperframes models install parakeet"
    elif npx --yes hyperframes models install parakeet --json >/dev/null 2>&1; then
      ok "Parakeet transcription installed"
    else
      bad "Parakeet install failed"; note "Run: npx hyperframes models install parakeet"
    fi
  elif command -v whisper-cli >/dev/null 2>&1 || command -v whisper-cpp >/dev/null 2>&1; then
    ok "whisper.cpp transcription"
  else
    bad "no transcriber for lyric timing"
    case "$OS" in
      Darwin) note "brew install whisper-cpp" ;;
      Linux)  note "build whisper.cpp (https://github.com/ggerganov/whisper.cpp) and put whisper-cli on PATH" ;;
      *)      note "download whisper.cpp for Windows (https://github.com/ggerganov/whisper.cpp/releases) and put whisper-cli on PATH" ;;
    esac
  fi
fi

if [ "$MUSIC_TEST" = 1 ]; then
  echo
  T="$HOME/motion-studio/_music-test"
  mkdir -p "$T/audio"
  cat > "$T/audio/song.json" <<'JSON'
{"title": "test", "mode": "score", "instrumental": true, "bpm": 120, "duration": 12, "seeds": [7],
 "caption": "Short warm cinematic electronic cue: soft piano, then pulsing synth bass and drums, bright and hopeful.",
 "lyrics": "[Intro - piano]\n\n[Build - drums enter]"}
JSON
  echo "  … generating a 12 s test score (model load + 1 take; 2-5 minutes)"
  if [ "$(free_gb "$HOME")" -lt 10 ]; then
    bad "only $(free_gb "$HOME") GB free disk: music generation needs ~10 GB free (swap), or a 16 GB computer can restart"
  elif bash "$SKILL_DIR/scripts/music/run_music.sh" "$T" > "$T/run.log" 2>&1 && [ -f "$T/audio/takes/seed7.wav" ]; then
    ok "music studio works: $T/audio/takes/seed7.wav"
  else
    bad "test generation failed: see $T/audio/gen.log and decode.log"
  fi
fi

echo
if [ "$problems" -eq 0 ]; then
  echo "All set."
else
  echo "$problems thing(s) to fix above, then run this again."
  exit 1
fi
