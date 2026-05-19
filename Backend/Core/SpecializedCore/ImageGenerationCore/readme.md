# ImageGenerationCore

The local latent diffusion pipeline. ImageGenerationCore generates images from text prompts entirely on local hardware using PyTorch-based diffusion math — no cloud APIs, no third-party inference services.

## Responsibility

Accept a text prompt and produce an image (base64-encoded PNG) using a local diffusion model. Falls back gracefully if VRAM is insufficient or model weights are unavailable.

## Supported Actions

| Action | Description |
|---|---|
| `generate_image` | Text-to-image from a prompt string |
| `get_status` | Return current GPU/VRAM state and model availability |

## VRAM Guard System

Before attempting generation, ImageGenerationCore checks available VRAM:

| VRAM Available | Action |
|---|---|
| ≥ 4 GB | Full-quality generation at configured resolution |
| 2–4 GB | Reduced resolution / fewer denoising steps |
| < 2 GB | Graceful fallback: returns an ASCII art descriptor instead of an image |

## Model Backend

- Primary: SDXL-Turbo or compatible diffusion model (from local weights directory)
- Fallback: ASCII art description of the prompt (CPU-only, no VRAM required)
- Model weights expected at: `Models/image_generation/` (not yet populated — Stage 4 work)

## Key File

`ImageGenerationCore.py`

## OrchestratorCore Trigger Keywords

```
generate image, draw, render image, create image,
picture of, show me an image, make an image, paint
```

## Output Format

```json
{
  "status": "success",
  "image_base64": "iVBORw0KGgo...",
  "width": 512,
  "height": 512,
  "prompt": "original prompt",
  "generation_time_ms": 4200
}
```
