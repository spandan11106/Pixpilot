import base64
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.agents.image_designer import (
    ImageGenerationError,
    _image_size,
    build_flux_prompt,
)

# Minimal valid base64 JPEG data URI for testing
_FAKE_DATA_URI = "data:image/jpeg;base64," + base64.b64encode(
    b"\xff\xd8\xff" + b"\x00" * 10
).decode()


def test_build_flux_prompt_all_fields():
    blueprint = {
        "subject": "amber glass serum bottle",
        "style": "editorial product photography",
        "lighting": "soft diffused studio light",
        "background": "white marble surface",
        "composition": "centered, shallow depth of field",
        "color_palette": "warm cream and amber tones",
        "camera_angle": "Studio Eye-Level",
        "lighting_preset": "Studio Softlight",
        "negative_prompts": "blurry, low quality",
        "aspect_ratio": "1:1",
    }
    result = build_flux_prompt(blueprint)
    assert "amber glass serum bottle" in result
    assert "editorial product photography" in result
    assert "soft diffused studio light" in result
    assert "white marble surface" in result
    assert "centered, shallow depth of field" in result
    assert "warm cream and amber tones" in result
    assert "Studio Eye-Level" in result
    assert "Studio Softlight" in result
    # negative_prompts must NOT appear in the main prompt
    assert "blurry" not in result


def test_build_flux_prompt_missing_optional_fields():
    blueprint = {
        "subject": "ceramic mug",
        "style": "minimalist",
        "lighting": "natural light",
        "background": "wooden table",
        "composition": "rule of thirds",
        "color_palette": "earth tones",
    }
    result = build_flux_prompt(blueprint)
    assert "ceramic mug" in result
    assert isinstance(result, str)
    assert len(result) > 10


def test_image_size_known_ratios():
    assert _image_size("1:1") == "square_hd"
    assert _image_size("16:9") == "landscape_16_9"
    assert _image_size("9:16") == "portrait_16_9"
    assert _image_size("4:5") == {"width": 864, "height": 1080}


def test_image_size_unknown_defaults_to_square():
    assert _image_size("unknown") == "square_hd"
    assert _image_size("") == "square_hd"


def test_image_generation_error_is_exception():
    err = ImageGenerationError("fal failed")
    assert isinstance(err, Exception)
    assert str(err) == "fal failed"
