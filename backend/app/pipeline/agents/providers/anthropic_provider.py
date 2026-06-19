"""Anthropic Claude Vision provider for product analysis."""

import json
import logging
from typing import Any

import anthropic

from app.core.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-3-5-sonnet-20241022"


def _is_invalid_model_error(exc: anthropic.APIError) -> bool:
    """Return True when the error is specifically an invalid/unknown model name."""
    if isinstance(exc, anthropic.BadRequestError):
        msg = str(exc).lower()
        return "model" in msg and ("not found" in msg or "invalid" in msg or "does not exist" in msg)
    if isinstance(exc, anthropic.NotFoundError):
        return True
    return False


class AnthropicVisionProvider:
    """Analyzes product media using an Anthropic Claude vision model."""

    def __init__(self, api_key: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = settings.anthropic_vision_model or DEFAULT_MODEL

    async def analyze(
        self,
        product_image: str,
        reference_image: str | None = None,
        video_frames: list[str] | None = None,
        model_thumbnails: list[str] | None = None,
    ) -> dict[str, Any]:
        """Analyze product media using the configured Claude vision model."""
        content = self._build_prompt(
            product_image, reference_image, video_frames, model_thumbnails
        )

        model_to_use = self.model
        try:
            response = await self.client.messages.create(
                model=model_to_use,
                max_tokens=2000,
                messages=[{"role": "user", "content": content}],
            )
        except anthropic.APIError as e:
            if _is_invalid_model_error(e) and model_to_use != DEFAULT_MODEL:
                logger.warning(
                    f"Anthropic model '{model_to_use}' is invalid, retrying with default '{DEFAULT_MODEL}'"
                )
                model_to_use = DEFAULT_MODEL
                response = await self.client.messages.create(
                    model=model_to_use,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": content}],
                )
            else:
                logger.error(f"Anthropic API error: {e}")
                raise

        text = response.content[0].text
        profile = self._parse_response(text)
        profile["provider_used"] = "anthropic"
        profile["model_used"] = model_to_use
        profile["analysis_completeness"] = self._calculate_completeness(
            product_image, reference_image, video_frames, model_thumbnails
        )
        return profile

    def _build_prompt(
        self,
        product_image: str,
        reference_image: str | None,
        video_frames: list[str] | None,
        model_thumbnails: list[str] | None,
    ) -> list[dict]:
        """Build the multimodal prompt for Claude 3.5 Sonnet."""
        content = []

        # Add product image
        content.append(self._image_to_content(product_image, "Product image"))

        if reference_image:
            content.append(self._image_to_content(reference_image, "Reference/style image"))

        if video_frames:
            for i, frame in enumerate(video_frames[:5]):
                content.append(self._image_to_content(frame, f"Video frame {i+1}"))

        if model_thumbnails:
            for i, thumbnail in enumerate(model_thumbnails[:4]):
                content.append(self._image_to_content(thumbnail, f"3D model view {i+1}"))

        # Add text prompt
        content.append(
            {
                "type": "text",
                "text": self._get_analysis_prompt(
                    reference_image is not None,
                    bool(video_frames),
                    bool(model_thumbnails),
                ),
            }
        )

        return content

    def _image_to_content(self, data_uri: str, label: str) -> dict[str, Any]:
        """Convert data URI to Claude's image format."""
        if data_uri.startswith("data:image/"):
            # Extract base64 from data URI
            header, data = data_uri.split(",", 1)
            media_type_part = header.replace("data:", "").replace(";base64", "")
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type_part,
                    "data": data,
                },
            }
        raise ValueError(f"Invalid data URI format for {label}")

    def _get_analysis_prompt(
        self, has_reference: bool, has_video: bool, has_3d: bool
    ) -> str:
        """Generate the analysis prompt based on available media."""
        media_hints = []
        if has_reference:
            media_hints.append(
                "A reference/style image is included showing the desired visual direction."
            )
        if has_video:
            media_hints.append("Multiple video frames show the product in motion and usage.")
        if has_3d:
            media_hints.append("3D model thumbnails from different perspectives are included.")

        media_context = " ".join(media_hints) if media_hints else ""

        reference_field = (
            '"inferred_style_from_reference": {"vibe": "...", "background_type": "...", "lighting": "...", "composition": "..."}'
            if has_reference
            else '"inferred_style_from_reference": null'
        )

        return f"""Analyze the provided product image(s) in detail and extract structured product information.

{media_context}

Return a JSON object with these fields:
{{
  "product_category": "category of the product (e.g., cosmetic bottle, furniture, apparel)",
  "dominant_colors": ["hex color code", ...],
  "materials_textures": ["material description", ...],
  "usps": ["unique selling point", ...],
  "product_shape": "basic shape (e.g., cylinder, rectangular, organic)",
  "lighting_conditions": "describe the lighting in the current product image",
  "surface_finish": "matte, glossy, textured, metallic, etc.",
  "scale_proportion": "is this a small handheld item, medium, large, etc.",
  {reference_field}
}}

Return ONLY valid JSON, no additional text."""

    def _parse_response(self, text: str) -> dict[str, Any]:
        """Parse JSON response from Claude."""
        try:
            # Extract JSON from the response
            json_start = text.find("{")
            json_end = text.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = text[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON object found in response")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Anthropic response: {text}")
            raise ValueError(f"Invalid JSON in response: {e}") from e

    def _calculate_completeness(
        self,
        product_image: str,
        reference_image: str | None,
        video_frames: list[str] | None,
        model_thumbnails: list[str] | None,
    ) -> float:
        """Calculate how complete the analysis was (0.0-1.0)."""
        score = 0.3  # Base score for product image
        if reference_image:
            score += 0.2
        if video_frames:
            score += 0.25
        if model_thumbnails:
            score += 0.25
        return min(1.0, score)
