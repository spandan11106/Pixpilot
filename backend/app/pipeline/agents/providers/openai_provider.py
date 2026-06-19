"""OpenAI GPT-4o Vision provider for product analysis."""

import json
import logging
from typing import Any

import openai

from app.core.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o"


def _is_invalid_model_error(exc: openai.APIError) -> bool:
    """Return True when the error is specifically an invalid/unknown model name."""
    if isinstance(exc, openai.NotFoundError):
        return True
    msg = str(exc).lower()
    return "model" in msg and ("not found" in msg or "does not exist" in msg or "invalid" in msg)


class OpenAIVisionProvider:
    """Analyzes product media using OpenAI's GPT-4o Vision model."""

    def __init__(self, api_key: str):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = settings.openai_vision_model or DEFAULT_MODEL

    async def analyze(
        self,
        product_image: str,
        reference_image: str | None = None,
        video_frames: list[str] | None = None,
        model_thumbnails: list[str] | None = None,
    ) -> dict[str, Any]:
        """Analyze product media using GPT-4o Vision."""
        content = self._build_prompt(
            product_image, reference_image, video_frames, model_thumbnails
        )

        model_to_use = self.model
        try:
            response = await self.client.chat.completions.create(
                model=model_to_use,
                max_tokens=2000,
                messages=[{"role": "user", "content": content}],
            )
        except openai.APIError as e:
            if _is_invalid_model_error(e) and model_to_use != DEFAULT_MODEL:
                logger.warning(
                    f"OpenAI model '{model_to_use}' is invalid, retrying with default '{DEFAULT_MODEL}'"
                )
                model_to_use = DEFAULT_MODEL
                response = await self.client.chat.completions.create(
                    model=model_to_use,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": content}],
                )
            else:
                logger.error(f"OpenAI API error: {e}")
                raise

        text = response.choices[0].message.content
        profile = self._parse_response(text)
        profile["provider_used"] = "openai"
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
        """Build the multimodal prompt for GPT-4o Vision."""
        content = []

        # Add images in the content
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": product_image},
            }
        )

        if reference_image:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": reference_image},
                }
            )

        if video_frames:
            for frame in video_frames[:5]:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": frame},
                    }
                )

        if model_thumbnails:
            for thumbnail in model_thumbnails[:4]:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": thumbnail},
                    }
                )

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

    def _get_analysis_prompt(
        self, has_reference: bool, has_video: bool, has_3d: bool
    ) -> str:
        """Generate the analysis prompt based on available media."""
        media_hints = []
        if has_reference:
            media_hints.append(
                "The second image shows a reference/style guide for visual direction."
            )
        if has_video:
            media_hints.append("Video frames are included showing the product in motion.")
        if has_3d:
            media_hints.append("3D model thumbnails from different angles are included.")

        media_context = " ".join(media_hints) if media_hints else ""

        reference_field = (
            '"inferred_style_from_reference": {"vibe": "...", "background_type": "...", "lighting": "...", "composition": "..."}'
            if has_reference
            else '"inferred_style_from_reference": null'
        )

        return f"""Analyze this product image in detail and extract structured product information.

{media_context}

Return a JSON object with the following fields:
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
        """Parse JSON response from GPT-4o."""
        try:
            # Extract JSON from the response (in case there's extra text)
            json_start = text.find("{")
            json_end = text.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = text[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON object found in response")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response: {text}")
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
