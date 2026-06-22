"""Tests for the Summary Agent — summary card and image prompt generation."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


SAMPLE_TEXT_RESULTS = {
    "product": {"content": "Organic cold-pressed argan oil, 30ml amber dropper bottle. Anti-aging, moisturising."},
    "audience": {"content": "Women aged 28–45 interested in natural skincare and clean beauty."},
    "colors": {"content": "Soft pastel pinks, warm cream tones, and matte gold accents."},
}

SAMPLE_PROFILE = {
    "product_category": "cosmetic bottle",
    "dominant_colors": ["#F5E6D3", "#C8A882"],
    "materials_textures": ["amber glass", "matte black plastic cap"],
    "usps": ["organic cold-pressed oil", "dropper bottle"],
    "product_shape": "cylinder",
    "inferred_style_from_reference": {
        "vibe": "warm minimalism",
        "background_type": "linen fabric, stone tray",
        "lighting": "golden hour soft side light",
        "composition": "centered product, negative space left side",
    },
    "provider_used": "openai",
    "analysis_completeness": 1.0,
}

SAMPLE_STEERING = {
    "aspect_ratio": "1:1",
    "camera_perspective": "Studio Eye-Level",
    "lighting_preset": "Studio Softlight",
    "negative_prompts": "blurry, watermark, text overlay",
}

SAMPLE_SUMMARY_CARD = {
    "product_name": "Argan Oil Serum",
    "product_category": "cosmetic bottle",
    "key_features": ["organic cold-pressed oil", "amber dropper bottle", "anti-aging"],
    "target_audience": "Women aged 28–45 interested in natural skincare",
    "dominant_colors": ["#F5E6D3", "#C8A882"],
    "materials": ["amber glass", "matte black plastic cap"],
    "style_vibe": "warm minimalism",
    "vision_available": True,
}


def _make_anthropic_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = [MagicMock(text=content)]
    return msg


# ── _parse_json ────────────────────────────────────────────────────────────────

class TestParseJson:
    def test_parses_clean_json(self):
        from app.pipeline.agents.summary_agent import _parse_json
        result = _parse_json('{"key": "value"}', "test")
        assert result == {"key": "value"}

    def test_extracts_json_from_surrounding_text(self):
        from app.pipeline.agents.summary_agent import _parse_json
        result = _parse_json('Here is the result:\n{"key": "value"}\nDone.', "test")
        assert result == {"key": "value"}

    def test_raises_on_no_json(self):
        from app.pipeline.agents.summary_agent import _parse_json
        with pytest.raises(ValueError, match="No JSON object found"):
            _parse_json("no json here", "test")

    def test_raises_on_invalid_json(self):
        from app.pipeline.agents.summary_agent import _parse_json
        with pytest.raises(ValueError, match="Invalid JSON"):
            _parse_json("{bad json: [}", "test")


# ── generate_summary_card ──────────────────────────────────────────────────────

class TestGenerateSummaryCard:
    @pytest.mark.asyncio
    async def test_returns_summary_card_with_vision(self):
        from app.pipeline.agents.summary_agent import generate_summary_card

        response_json = json.dumps(SAMPLE_SUMMARY_CARD)
        mock_response = _make_anthropic_response(response_json)

        with patch("app.pipeline.agents.summary_agent.settings") as mock_settings, \
             patch("app.pipeline.agents.summary_agent.anthropic.AsyncAnthropic") as mock_cls:
            mock_settings.anthropic_api_key = "sk-ant-test"
            mock_settings.summary_model = "claude-haiku-4-5"
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            result = await generate_summary_card(SAMPLE_TEXT_RESULTS, SAMPLE_PROFILE)

        assert result["vision_available"] is True
        assert result["product_name"] == "Argan Oil Serum"
        assert result["product_category"] == "cosmetic bottle"

    @pytest.mark.asyncio
    async def test_proceeds_without_vision_profile(self):
        from app.pipeline.agents.summary_agent import generate_summary_card

        card_no_vision = {**SAMPLE_SUMMARY_CARD, "vision_available": False}
        mock_response = _make_anthropic_response(json.dumps(card_no_vision))

        with patch("app.pipeline.agents.summary_agent.settings") as mock_settings, \
             patch("app.pipeline.agents.summary_agent.anthropic.AsyncAnthropic") as mock_cls:
            mock_settings.anthropic_api_key = "sk-ant-test"
            mock_settings.summary_model = "claude-haiku-4-5"
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            result = await generate_summary_card(SAMPLE_TEXT_RESULTS, product_profile=None)

        assert result["vision_available"] is False

    @pytest.mark.asyncio
    async def test_prompt_contains_user_description(self):
        from app.pipeline.agents.summary_agent import generate_summary_card

        mock_response = _make_anthropic_response(json.dumps(SAMPLE_SUMMARY_CARD))
        captured_prompt = {}

        async def capture_create(**kwargs):
            captured_prompt["messages"] = kwargs["messages"]
            return mock_response

        with patch("app.pipeline.agents.summary_agent.settings") as mock_settings, \
             patch("app.pipeline.agents.summary_agent.anthropic.AsyncAnthropic") as mock_cls:
            mock_settings.anthropic_api_key = "sk-ant-test"
            mock_settings.summary_model = "claude-haiku-4-5"
            mock_client = AsyncMock()
            mock_client.messages.create = capture_create
            mock_cls.return_value = mock_client

            await generate_summary_card(SAMPLE_TEXT_RESULTS, SAMPLE_PROFILE)

        prompt_text = captured_prompt["messages"][0]["content"]
        assert "argan oil" in prompt_text.lower()
        assert "28–45" in prompt_text

    @pytest.mark.asyncio
    async def test_raises_on_missing_api_key(self):
        from app.pipeline.agents.summary_agent import generate_summary_card

        with patch("app.pipeline.agents.summary_agent.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""

            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                await generate_summary_card(SAMPLE_TEXT_RESULTS, SAMPLE_PROFILE)


# ── generate_image_prompt ──────────────────────────────────────────────────────

class TestGenerateImagePrompt:
    @pytest.mark.asyncio
    async def test_returns_structured_prompt(self):
        from app.pipeline.agents.summary_agent import generate_image_prompt

        blueprint = {
            "subject": "amber glass dropper bottle, matte black cap",
            "style": "luxury product photography, warm minimalism",
            "lighting": "golden hour soft side light",
            "background": "linen fabric, stone tray",
            "composition": "centered product, negative space left side",
            "color_palette": "soft pastel pinks, warm cream, matte gold",
            "camera_angle": "Studio Eye-Level",
            "aspect_ratio": "1:1",
            "negative_prompts": "blurry, watermark",
            "lighting_preset": "Studio Softlight",
        }
        mock_response = _make_anthropic_response(json.dumps(blueprint))

        with patch("app.pipeline.agents.summary_agent.settings") as mock_settings, \
             patch("app.pipeline.agents.summary_agent.anthropic.AsyncAnthropic") as mock_cls:
            mock_settings.anthropic_api_key = "sk-ant-test"
            mock_settings.prompt_model = "claude-sonnet-4-6"
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            result = await generate_image_prompt(SAMPLE_SUMMARY_CARD, SAMPLE_STEERING)

        assert result["subject"] is not None
        assert result["aspect_ratio"] == "1:1"
        assert result["camera_angle"] == "Studio Eye-Level"

    @pytest.mark.asyncio
    async def test_steering_passthrough_fallback(self):
        """Steering fields are set even if the model omits them."""
        from app.pipeline.agents.summary_agent import generate_image_prompt

        # Response missing all steering fields
        incomplete = {"subject": "bottle", "style": "clean", "lighting": "soft",
                      "background": "white", "composition": "centered", "color_palette": "neutral"}
        mock_response = _make_anthropic_response(json.dumps(incomplete))

        with patch("app.pipeline.agents.summary_agent.settings") as mock_settings, \
             patch("app.pipeline.agents.summary_agent.anthropic.AsyncAnthropic") as mock_cls:
            mock_settings.anthropic_api_key = "sk-ant-test"
            mock_settings.prompt_model = "claude-sonnet-4-6"
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            result = await generate_image_prompt(SAMPLE_SUMMARY_CARD, SAMPLE_STEERING)

        assert result["aspect_ratio"] == "1:1"
        assert result["camera_angle"] == "Studio Eye-Level"
        assert result["lighting_preset"] == "Studio Softlight"
        assert result["negative_prompts"] == "blurry, watermark, text overlay"
