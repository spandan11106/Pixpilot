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
