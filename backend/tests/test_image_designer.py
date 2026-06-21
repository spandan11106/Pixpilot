import base64
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.agents.image_designer import (
    ImageGenerationError,
    _image_size,
    build_flux_prompt,
    generate_image,
)
from app.core.settings import settings

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


@pytest.mark.asyncio
async def test_generate_image_success():
    fake_result = {
        "images": [{"url": "https://fal.media/files/abc/output.jpg"}],
        "seed": 42,
        "timings": {"inference": 3.1},
    }
    with patch.object(settings, "fal_api_key", "fake-key"), \
         patch("fal_client.upload", return_value="https://fal.storage/uploaded.jpg"), \
         patch("fal_client.run_async", new=AsyncMock(return_value=fake_result)):
        result = await generate_image(
            prompt="luxury serum bottle on marble",
            image_data_uri=_FAKE_DATA_URI,
            aspect_ratio="1:1",
            negative_prompts="blurry",
        )
    assert result["image_url"] == "https://fal.media/files/abc/output.jpg"
    assert result["seed"] == 42
    assert isinstance(result["latency_ms"], int)


@pytest.mark.asyncio
async def test_generate_image_passes_seed():
    fake_result = {"images": [{"url": "https://fal.media/out.jpg"}], "seed": 99}
    with patch.object(settings, "fal_api_key", "fake-key"), \
         patch("fal_client.upload", return_value="https://fal.storage/img.jpg"), \
         patch("fal_client.run_async", new=AsyncMock(return_value=fake_result)) as mock_run:
        await generate_image(
            prompt="test",
            image_data_uri=_FAKE_DATA_URI,
            aspect_ratio="1:1",
            negative_prompts="",
            seed=99,
        )
    assert mock_run.call_args[1]["arguments"]["seed"] == 99


@pytest.mark.asyncio
async def test_generate_image_retries_then_raises():
    with patch.object(settings, "fal_api_key", "fake-key"), \
         patch("fal_client.upload", return_value="https://fal.storage/img.jpg"), \
         patch("fal_client.run_async", new=AsyncMock(side_effect=RuntimeError("timeout"))), \
         patch("asyncio.sleep", new=AsyncMock()):
        with pytest.raises(ImageGenerationError, match="3 attempts"):
            await generate_image(
                prompt="test",
                image_data_uri=_FAKE_DATA_URI,
                aspect_ratio="1:1",
                negative_prompts="",
            )


@pytest.mark.asyncio
async def test_generate_image_raises_if_no_images():
    fake_result = {"images": [], "seed": 1}
    with patch.object(settings, "fal_api_key", "fake-key"), \
         patch("fal_client.upload", return_value="https://fal.storage/img.jpg"), \
         patch("fal_client.run_async", new=AsyncMock(return_value=fake_result)), \
         patch("asyncio.sleep", new=AsyncMock()):
        with pytest.raises(ImageGenerationError):
            await generate_image(
                prompt="test",
                image_data_uri=_FAKE_DATA_URI,
                aspect_ratio="1:1",
                negative_prompts="",
            )


@pytest.mark.asyncio
async def test_generate_image_no_fal_key_raises():
    with patch.object(settings, "fal_api_key", ""):
        os.environ.pop("FAL_KEY", None)
        with pytest.raises(ImageGenerationError, match="FAL_KEY"):
            await generate_image(
                prompt="test",
                image_data_uri=_FAKE_DATA_URI,
                aspect_ratio="1:1",
                negative_prompts="",
            )
