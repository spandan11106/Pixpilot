"""Image Designer Agent — FLUX prompt builder, fal.ai client, Refinement Agent."""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import time
from typing import Any

import anthropic
import httpx

from app.core.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_REFINEMENT_MODEL = "claude-sonnet-4-6"

_ASPECT_RATIO_MAP: dict[str, str | dict] = {
    "1:1": "square_hd",
    "16:9": "landscape_16_9",
    "9:16": "portrait_16_9",
    "4:5": {"width": 864, "height": 1080},
}


class ImageGenerationError(Exception):
    pass


def _image_size(aspect_ratio: str) -> str | dict:
    return _ASPECT_RATIO_MAP.get(aspect_ratio, "square_hd")


def _ensure_fal_key() -> None:
    key = settings.fal_api_key or os.environ.get("FAL_KEY", "")
    if not key:
        raise ImageGenerationError(
            "FAL_KEY is not configured. Set fal_api_key in .env."
        )
    os.environ["FAL_KEY"] = key


async def generate_image(
    prompt: str,
    image_data_uri: str,
    aspect_ratio: str = "1:1",
    negative_prompts: str = "",
    seed: int | None = None,
) -> dict[str, Any]:
    """Submit an image-to-image job to fal.ai and return the result.

    Returns dict with keys: image_url (str), seed (int | None), latency_ms (int).
    Raises ImageGenerationError after 3 failed attempts.
    """
    import fal_client  # late import so tests can patch at the module level

    _ensure_fal_key()

    # Decode the base64 data URI to raw bytes, then upload to fal storage
    _, b64 = image_data_uri.split(",", 1)
    image_bytes = base64.b64decode(b64)
    image_url = fal_client.upload(image_bytes, "image/jpeg")

    arguments: dict[str, Any] = {
        "prompt": prompt,
        "image_url": image_url,
        "image_size": _image_size(aspect_ratio),
        "num_inference_steps": 28,
        "strength": 0.85,
        "num_images": 1,
    }
    if negative_prompts:
        arguments["negative_prompt"] = negative_prompts
    if seed is not None:
        arguments["seed"] = seed

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            start = time.monotonic()
            result = await fal_client.run_async(settings.fal_image_model, arguments=arguments)
            latency_ms = int((time.monotonic() - start) * 1000)

            images = result.get("images", [])
            if not images:
                raise ImageGenerationError("fal.ai returned no images in response")

            return {
                "image_url": images[0]["url"],
                "seed": result.get("seed"),
                "latency_ms": latency_ms,
            }
        except ImageGenerationError:
            raise
        except Exception as e:
            last_error = e
            logger.warning(f"fal.ai attempt {attempt + 1}/3 failed: {e}")
            if attempt < 2:
                await asyncio.sleep(2)

    raise ImageGenerationError(
        f"fal.ai failed after 3 attempts: {last_error}"
    ) from last_error


def build_flux_prompt(blueprint: dict[str, Any]) -> str:
    """Assemble creative_blueprint fields into a single FLUX prompt string."""
    core_parts = [
        blueprint.get("subject", ""),
        blueprint.get("style", ""),
        blueprint.get("lighting", ""),
        blueprint.get("background", ""),
        blueprint.get("composition", ""),
        blueprint.get("color_palette", ""),
    ]
    prompt = ". ".join(p for p in core_parts if p)
    if prompt and not prompt.endswith("."):
        prompt += "."
    if blueprint.get("camera_angle"):
        prompt += f" Camera: {blueprint['camera_angle']}."
    if blueprint.get("lighting_preset"):
        prompt += f" Lighting preset: {blueprint['lighting_preset']}."
    return prompt.strip()
