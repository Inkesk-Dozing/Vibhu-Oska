"""
Vibhu-Oska AI-OS — ImageGenerationCore
Localized Latent Diffusion Pipeline — Text-to-Image on Local GPU.

Attempts to use a locally installed diffusion pipeline (diffusers + torch).
Falls back to a structured generation descriptor when the GPU pipeline is
unavailable or VRAM is insufficient for the requested resolution.

IMPORTANT: This module uses PyTorch and the diffusers library. It does NOT
call any cloud API endpoints. All inference is local and private.
"""

from __future__ import annotations

import asyncio
import base64
import io
import time
from pathlib import Path
from typing import Any

from Backend.Plugins.Logger.Logger import Logger
from Backend.Plugins.ToolRegistry.BaseService import BaseService
from Shared.Models import PluginInfo, CoreStatus, ExecutionTarget


# VRAM guard thresholds (bytes)
_MIN_VRAM_BYTES_FOR_SD: int = 4 * 1024 ** 3   # 4 GB minimum for diffusion
_VRAM_SAFE_HEADROOM: int = 1 * 1024 ** 3       # Reserve 1 GB headroom

# Default generation parameters
_DEFAULT_WIDTH:  int = 512
_DEFAULT_HEIGHT: int = 512
_DEFAULT_STEPS:  int = 20
_MAX_WIDTH:      int = 1024
_MAX_HEIGHT:     int = 1024


class ImageGenerationCore(BaseService):
    """
    ImageGenerationCore — local text-to-image pipeline on the Vibhu-Oska GPU.

    Operates exclusively on local hardware. Checks VRAM availability before
    firing the diffusion pipeline. If resources are insufficient, returns a
    structured image descriptor that can be used by DesignCore or the frontend
    as a placeholder/wireframe specification.

    Supported actions (via execute()):
    - generate_image    → produce a base64-encoded PNG from a text prompt
    - get_pipeline_info → return current pipeline status and VRAM headroom
    - check_resources   → return VRAM availability and model load state
    """

    def __init__(self) -> None:
        self._initialized: bool = False
        self._pipeline: Any = None   # diffusers StableDiffusionPipeline or None
        self._pipeline_id: str = ""
        self._log = Logger.get("ImageGenerationCore")

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    def info(self) -> PluginInfo:
        """Return plugin metadata."""
        pipeline_loaded = self._pipeline is not None
        return PluginInfo(
            name="image_generation",
            version="1.0.0",
            description="Localized latent diffusion text-to-image pipeline — runs on local GPU silicon",
            capabilities=["text_to_image", "diffusion_pipeline"],
            status=CoreStatus.HEALTHY if self._initialized else CoreStatus.UNKNOWN,
            preferred_target=ExecutionTarget.GPU,
        )

    def health_check(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        """
        Initialize ImageGenerationCore.

        Parameters: none
        Returns: none
        Edge cases: Does NOT eagerly load the pipeline (heavy VRAM allocation). Pipeline loads lazily on first generate call.
        """
        if self._initialized:
            return
        self._initialized = True
        self._log.info("ImageGenerationCore initialized (pipeline loads lazily on first generation request)")

    async def execute(self, action: str, **kwargs: Any) -> Any:
        """
        Dispatch an image generation action.

        Parameters:
            action: One of generate_image, get_pipeline_info, check_resources
            **kwargs: Action-specific arguments
        Returns: dict result
        Edge cases: Unknown actions raise ValueError
        """
        if not self._initialized:
            await self.initialize()

        dispatch = {
            "generate_image":    self._generate_image,
            "get_pipeline_info": self._get_pipeline_info,
            "check_resources":   self._check_resources,
        }

        if action not in dispatch:
            raise ValueError(
                f"Action '{action}' not supported by ImageGenerationCore. "
                f"Available: {sorted(dispatch.keys())}"
            )

        return await dispatch[action](**kwargs)

    def process(self, data: Any) -> Any:
        return data

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    async def _check_resources(self, **_: Any) -> dict[str, Any]:
        """
        Check VRAM availability and pipeline load state.

        Parameters: none
        Returns: dict with vram_total_gb, vram_free_gb, pipeline_loaded, cuda_available, sufficient_vram
        Edge cases: Returns cuda_available=False gracefully if torch not installed
        """
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            if not cuda_available:
                return {
                    "cuda_available": False,
                    "pipeline_loaded": False,
                    "message": "CUDA not available. Image generation requires an NVIDIA GPU with CUDA support.",
                }

            total = torch.cuda.get_device_properties(0).total_memory
            reserved = torch.cuda.memory_reserved(0)
            free = total - reserved

            sufficient = free >= (_MIN_VRAM_BYTES_FOR_SD + _VRAM_SAFE_HEADROOM)

            return {
                "cuda_available": True,
                "pipeline_loaded": self._pipeline is not None,
                "pipeline_id": self._pipeline_id or "none",
                "vram_total_gb": round(total / 1024 ** 3, 2),
                "vram_reserved_gb": round(reserved / 1024 ** 3, 2),
                "vram_free_gb": round(free / 1024 ** 3, 2),
                "sufficient_vram": sufficient,
                "min_required_gb": round(_MIN_VRAM_BYTES_FOR_SD / 1024 ** 3, 1),
            }

        except ImportError:
            return {
                "cuda_available": False,
                "pipeline_loaded": False,
                "message": "PyTorch not installed. Install torch with CUDA support.",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _get_pipeline_info(self, **_: Any) -> dict[str, Any]:
        """
        Return current pipeline status and configuration.

        Parameters: none
        Returns: dict with pipeline_id, loaded, model_config_summary
        Edge cases: Returns empty config if pipeline not loaded
        """
        resources = await self._check_resources()
        return {
            "pipeline_id": self._pipeline_id or "not loaded",
            "loaded": self._pipeline is not None,
            "resources": resources,
            "supported_models": [
                "stabilityai/sdxl-turbo",
                "runwayml/stable-diffusion-v1-5",
                "CompVis/stable-diffusion-v1-4",
            ],
        }

    async def _generate_image(
        self,
        prompt: str,
        negative_prompt: str = "blurry, low quality, distorted, watermark",
        width: int = _DEFAULT_WIDTH,
        height: int = _DEFAULT_HEIGHT,
        num_inference_steps: int = _DEFAULT_STEPS,
        guidance_scale: float = 7.5,
        model_id: str = "stabilityai/sdxl-turbo",
        **_: Any,
    ) -> dict[str, Any]:
        """
        Generate an image from a text prompt using the local diffusion pipeline.

        Parameters:
            prompt: Text description of the desired image
            negative_prompt: Things to avoid in the generated image
            width: Image width in pixels (max 1024, default 512)
            height: Image height in pixels (max 1024, default 512)
            num_inference_steps: Diffusion steps (more = higher quality, slower)
            guidance_scale: How strictly to follow the prompt (7.5 = balanced)
            model_id: HuggingFace model ID for the pipeline
        Returns: dict with status, image_base64, mime_type, width, height, elapsed_ms
                 OR status=fallback with descriptor if VRAM insufficient
        Edge cases: VRAM check runs before loading pipeline; if insufficient returns
                    structured descriptor instead of raising
        """
        # Clamp dimensions
        width  = min(max(64, width), _MAX_WIDTH)
        height = min(max(64, height), _MAX_HEIGHT)

        self._log.info(
            "Image generation requested",
            prompt=prompt[:80],
            width=width,
            height=height,
            steps=num_inference_steps,
            model_id=model_id,
        )

        # Resource check first
        resources = await self._check_resources()
        if not resources.get("cuda_available"):
            return self._fallback_descriptor(prompt, width, height, reason="CUDA not available")

        if not resources.get("sufficient_vram"):
            return self._fallback_descriptor(
                prompt, width, height,
                reason=f"Insufficient VRAM: {resources.get('vram_free_gb', 0):.1f}GB free, "
                       f"{resources.get('min_required_gb', 4)}GB required"
            )

        # Load pipeline lazily
        if self._pipeline is None or self._pipeline_id != model_id:
            load_result = await asyncio.to_thread(self._load_pipeline, model_id)
            if not load_result:
                return self._fallback_descriptor(prompt, width, height, reason="Pipeline load failed — check logs")

        # Run inference in thread pool
        start = time.time()
        try:
            image_bytes = await asyncio.to_thread(
                self._run_inference,
                prompt, negative_prompt, width, height, num_inference_steps, guidance_scale
            )
            elapsed_ms = round((time.time() - start) * 1000)

            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            self._log.info("Image generated successfully", elapsed_ms=elapsed_ms, width=width, height=height)

            return {
                "status": "success",
                "image_base64": image_b64,
                "mime_type": "image/png",
                "width": width,
                "height": height,
                "elapsed_ms": elapsed_ms,
                "model_id": model_id,
                "prompt": prompt,
            }

        except Exception as e:
            self._log.error("Image generation inference failed", error=str(e))
            return self._fallback_descriptor(prompt, width, height, reason=f"Inference error: {str(e)}")

    def _load_pipeline(self, model_id: str) -> bool:
        """
        Load the diffusion pipeline into GPU memory.

        Parameters:
            model_id: HuggingFace model identifier
        Returns: True if loaded successfully, False otherwise
        Edge cases: ImportError (diffusers not installed) returns False gracefully
        """
        try:
            import torch
            from diffusers import AutoPipelineForText2Image

            self._log.info(f"Loading diffusion pipeline: {model_id}")
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32

            pipe = AutoPipelineForText2Image.from_pretrained(
                model_id,
                torch_dtype=dtype,
                variant="fp16" if dtype == torch.float16 else None,
            )
            pipe = pipe.to("cuda" if torch.cuda.is_available() else "cpu")

            # Enable memory optimizations
            if hasattr(pipe, "enable_attention_slicing"):
                pipe.enable_attention_slicing()
            if hasattr(pipe, "enable_vae_slicing"):
                pipe.enable_vae_slicing()

            self._pipeline = pipe
            self._pipeline_id = model_id
            self._log.info("Diffusion pipeline loaded", model_id=model_id)
            return True

        except ImportError:
            self._log.warning(
                "diffusers library not installed. Install with: pip install diffusers accelerate"
            )
            return False
        except Exception as e:
            self._log.error("Pipeline load failed", model_id=model_id, error=str(e))
            return False

    def _run_inference(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        guidance_scale: float,
    ) -> bytes:
        """
        Run the diffusion inference synchronously (called from thread pool).

        Parameters:
            prompt: Positive prompt text
            negative_prompt: Negative prompt text
            width, height: Output image dimensions
            steps: Number of diffusion denoising steps
            guidance_scale: CFG scale for prompt adherence
        Returns: PNG image bytes
        Edge cases: All tensor errors propagate up to the async caller
        """
        output = self._pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
        )
        image = output.images[0]
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    @staticmethod
    def _fallback_descriptor(
        prompt: str,
        width: int,
        height: int,
        reason: str = "Diffusion pipeline unavailable",
    ) -> dict[str, Any]:
        """
        Return a structured image descriptor when the diffusion pipeline cannot run.

        This allows the frontend and DesignCore to render a meaningful placeholder
        instead of receiving a raw error.

        Parameters:
            prompt: The original image prompt
            width, height: Requested dimensions
            reason: Human-readable explanation of why the pipeline was not used
        Returns: dict with status=fallback and descriptor fields
        Edge cases: none
        """
        return {
            "status": "fallback",
            "reason": reason,
            "descriptor": {
                "prompt": prompt,
                "width": width,
                "height": height,
                "type": "image_placeholder",
                "suggested_style": "dark futuristic AI-generated visual",
                "message": f"Local image generation unavailable: {reason}. "
                           f"Requested: {width}x{height}px — '{prompt[:100]}'",
            },
        }
