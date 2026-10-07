# Third-party components

Nothing third-party is bundled in this zip except a small patch file. Everything below is downloaded
from its official source by `scripts/setup.sh`, on your machine, under its own licence.

| component | how it's used | licence |
|---|---|---|
| HyperFrames CLI + skills | `npx hyperframes` / `npx hyperframes skills` | see github.com/heygen-com/hyperframes |
| ACE-Step 1.5 (code + models) | cloned from github.com/ACE-Step/ACE-Step-1.5, models from Hugging Face | MIT (see its repository and model cards) |
| `scripts/music/acestep-mps-bf16.patch` | 3-line local patch to ACE-Step (bfloat16 on Apple GPUs) | same as ACE-Step (MIT) |
| demucs | vocal / instrumental separation | MIT |
| Parakeet (via HyperFrames) / whisper.cpp | word timestamps | see their model cards / MIT |
| GSAP 3 | loaded from the jsDelivr CDN by compositions | GSAP standard licence (free, including commercial use) |
| uv | Python project manager used to run ACE-Step | MIT / Apache-2.0 |

Music you generate with ACE-Step and sound effects synthesized by `scripts/sfx/sfx_lib.py` are yours to use.
Fonts: use the HyperFrames bundled fonts or SIL Open Font License fonts (Google Fonts). Don't ship proprietary fonts.
