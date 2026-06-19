"""Tests for the Vision Agent and providers."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Unit tests ────────────────────────────────────────────────────────────────

class TestOpenAIProvider:
    def test_initialization(self):
        from app.pipeline.agents.providers.openai_provider import OpenAIVisionProvider
        p = OpenAIVisionProvider("test-key")
        assert p.model == "gpt-4o"

    def test_parse_valid_response(self):
        from app.pipeline.agents.providers.openai_provider import OpenAIVisionProvider
        p = OpenAIVisionProvider("test-key")
        result = p._parse_response('{"product_category": "bottle", "dominant_colors": ["#fff"]}')
        assert result["product_category"] == "bottle"

    def test_parse_response_with_surrounding_text(self):
        from app.pipeline.agents.providers.openai_provider import OpenAIVisionProvider
        p = OpenAIVisionProvider("test-key")
        result = p._parse_response('Here is the JSON:\n{"product_category": "jar"}\nDone.')
        assert result["product_category"] == "jar"

    def test_parse_invalid_response_raises(self):
        from app.pipeline.agents.providers.openai_provider import OpenAIVisionProvider
        p = OpenAIVisionProvider("test-key")
        with pytest.raises(ValueError):
            p._parse_response("no json here at all")

    def test_prompt_with_reference(self):
        from app.pipeline.agents.providers.openai_provider import OpenAIVisionProvider
        p = OpenAIVisionProvider("test-key")
        prompt = p._get_analysis_prompt(has_reference=True, has_video=False, has_3d=False)
        assert '"inferred_style_from_reference": {' in prompt
        assert "null" not in prompt.split("inferred_style_from_reference")[1][:5]

    def test_prompt_without_reference(self):
        from app.pipeline.agents.providers.openai_provider import OpenAIVisionProvider
        p = OpenAIVisionProvider("test-key")
        prompt = p._get_analysis_prompt(has_reference=False, has_video=False, has_3d=False)
        assert '"inferred_style_from_reference": null' in prompt

    def test_completeness_product_only(self):
        from app.pipeline.agents.providers.openai_provider import OpenAIVisionProvider
        p = OpenAIVisionProvider("test-key")
        score = p._calculate_completeness("img", None, None, None)
        assert score == pytest.approx(0.3)

    def test_completeness_all_media(self):
        from app.pipeline.agents.providers.openai_provider import OpenAIVisionProvider
        p = OpenAIVisionProvider("test-key")
        score = p._calculate_completeness("img", "ref", ["f1"], ["t1"])
        assert score == pytest.approx(1.0)


class TestAnthropicProvider:
    def test_initialization(self):
        from app.pipeline.agents.providers.anthropic_provider import AnthropicVisionProvider
        p = AnthropicVisionProvider("test-key")
        assert p.model == "claude-3-5-sonnet-20241022"

    def test_image_to_content_valid_uri(self):
        from app.pipeline.agents.providers.anthropic_provider import AnthropicVisionProvider
        p = AnthropicVisionProvider("test-key")
        part = p._image_to_content("data:image/jpeg;base64,abc123", "test")
        assert part["type"] == "image"
        assert part["source"]["type"] == "base64"
        assert part["source"]["media_type"] == "image/jpeg"
        assert part["source"]["data"] == "abc123"

    def test_image_to_content_invalid_uri_raises(self):
        from app.pipeline.agents.providers.anthropic_provider import AnthropicVisionProvider
        p = AnthropicVisionProvider("test-key")
        with pytest.raises(ValueError):
            p._image_to_content("not-a-data-uri", "test")

    def test_prompt_without_reference(self):
        from app.pipeline.agents.providers.anthropic_provider import AnthropicVisionProvider
        p = AnthropicVisionProvider("test-key")
        prompt = p._get_analysis_prompt(has_reference=False, has_video=True, has_3d=True)
        assert '"inferred_style_from_reference": null' in prompt
        assert "video frames" in prompt.lower()
        assert "3d model" in prompt.lower()


class TestGoogleProvider:
    def test_data_uri_to_part(self):
        import base64
        from app.pipeline.agents.providers.google_provider import GoogleVisionProvider
        # Build a minimal valid data URI
        raw = b"\xff\xd8\xff"  # JPEG magic bytes
        b64 = base64.b64encode(raw).decode()
        uri = f"data:image/jpeg;base64,{b64}"

        with patch("app.pipeline.agents.providers.google_provider.genai"), \
             patch("app.pipeline.agents.providers.google_provider.types") as mock_types:
            mock_part = MagicMock()
            mock_types.Part.from_bytes.return_value = mock_part

            p = GoogleVisionProvider("test-key")
            result = p._data_uri_to_part(uri, "test")

            mock_types.Part.from_bytes.assert_called_once_with(
                data=raw, mime_type="image/jpeg"
            )
            assert result == mock_part

    def test_data_uri_invalid_raises(self):
        from app.pipeline.agents.providers.google_provider import GoogleVisionProvider
        with patch("app.pipeline.agents.providers.google_provider.genai"):
            p = GoogleVisionProvider("test-key")
            with pytest.raises(ValueError):
                p._data_uri_to_part("not-a-data-uri", "test")

    def test_prompt_without_reference(self):
        from app.pipeline.agents.providers.google_provider import GoogleVisionProvider
        with patch("app.pipeline.agents.providers.google_provider.genai"):
            p = GoogleVisionProvider("test-key")
            prompt = p._get_analysis_prompt(has_reference=False, has_video=False, has_3d=False)
            assert '"inferred_style_from_reference": null' in prompt

    def test_prompt_with_reference(self):
        from app.pipeline.agents.providers.google_provider import GoogleVisionProvider
        with patch("app.pipeline.agents.providers.google_provider.genai"):
            p = GoogleVisionProvider("test-key")
            prompt = p._get_analysis_prompt(has_reference=True, has_video=False, has_3d=False)
            assert '"inferred_style_from_reference": {' in prompt


# ── Orchestrator tests ────────────────────────────────────────────────────────

class TestVisionOrchestrator:
    def test_priority_order_filtered_by_available_keys(self):
        with patch("app.pipeline.agents.vision_orchestrator.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-test"
            mock_settings.anthropic_api_key = ""
            mock_settings.google_api_key = ""
            mock_settings.vision_models = "openai,anthropic,google"

            with patch("app.pipeline.agents.vision_orchestrator.OpenAIVisionProvider"):
                from app.pipeline.agents.vision_orchestrator import VisionOrchestrator
                orch = VisionOrchestrator()
                order = orch.get_priority_order()
                assert order == ["openai"]
                assert "anthropic" not in order
                assert "google" not in order

    @pytest.mark.asyncio
    async def test_returns_first_successful_provider(self):
        with patch("app.pipeline.agents.vision_orchestrator.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-test"
            mock_settings.anthropic_api_key = "sk-ant"
            mock_settings.google_api_key = ""
            mock_settings.vision_models = "openai,anthropic"

            expected = {"product_category": "bottle", "provider_used": "openai", "analysis_completeness": 0.3}
            mock_openai = AsyncMock()
            mock_openai.analyze = AsyncMock(return_value=expected)

            mock_anthropic = AsyncMock()
            mock_anthropic.analyze = AsyncMock(return_value={"provider_used": "anthropic"})

            with patch("app.pipeline.agents.vision_orchestrator.OpenAIVisionProvider", return_value=mock_openai), \
                 patch("app.pipeline.agents.vision_orchestrator.AnthropicVisionProvider", return_value=mock_anthropic):
                from app.pipeline.agents.vision_orchestrator import VisionOrchestrator
                orch = VisionOrchestrator()
                result = await orch.analyze("data:image/jpeg;base64,abc")

        assert result["provider_used"] == "openai"
        mock_anthropic.analyze.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_to_second_provider_on_failure(self):
        with patch("app.pipeline.agents.vision_orchestrator.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-test"
            mock_settings.anthropic_api_key = "sk-ant"
            mock_settings.google_api_key = ""
            mock_settings.vision_models = "openai,anthropic"

            mock_openai = AsyncMock()
            mock_openai.analyze = AsyncMock(side_effect=Exception("API timeout"))

            expected = {"product_category": "bottle", "provider_used": "anthropic", "analysis_completeness": 0.3}
            mock_anthropic = AsyncMock()
            mock_anthropic.analyze = AsyncMock(return_value=expected)

            with patch("app.pipeline.agents.vision_orchestrator.OpenAIVisionProvider", return_value=mock_openai), \
                 patch("app.pipeline.agents.vision_orchestrator.AnthropicVisionProvider", return_value=mock_anthropic):
                from app.pipeline.agents.vision_orchestrator import VisionOrchestrator
                orch = VisionOrchestrator()
                result = await orch.analyze("data:image/jpeg;base64,abc")

        assert result["provider_used"] == "anthropic"
        mock_openai.analyze.assert_called_once()
        mock_anthropic.analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_all_providers_fail(self):
        with patch("app.pipeline.agents.vision_orchestrator.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-test"
            mock_settings.anthropic_api_key = "sk-ant"
            mock_settings.google_api_key = ""
            mock_settings.vision_models = "openai,anthropic"

            mock_openai = AsyncMock()
            mock_openai.analyze = AsyncMock(side_effect=Exception("OpenAI down"))
            mock_anthropic = AsyncMock()
            mock_anthropic.analyze = AsyncMock(side_effect=Exception("Anthropic down"))

            with patch("app.pipeline.agents.vision_orchestrator.OpenAIVisionProvider", return_value=mock_openai), \
                 patch("app.pipeline.agents.vision_orchestrator.AnthropicVisionProvider", return_value=mock_anthropic):
                from app.pipeline.agents.vision_orchestrator import VisionOrchestrator
                orch = VisionOrchestrator()
                result = await orch.analyze("data:image/jpeg;base64,abc")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_providers_configured(self):
        with patch("app.pipeline.agents.vision_orchestrator.settings") as mock_settings:
            mock_settings.openai_api_key = ""
            mock_settings.anthropic_api_key = ""
            mock_settings.google_api_key = ""
            mock_settings.vision_models = "openai,anthropic,google"

            from app.pipeline.agents.vision_orchestrator import VisionOrchestrator
            orch = VisionOrchestrator()
            result = await orch.analyze("data:image/jpeg;base64,abc")

        assert result is None
