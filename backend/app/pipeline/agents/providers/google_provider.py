"""Google Gemini Vision provider for product analysis."""

import base64
import json
import logging
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.core.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.0-flash"


def _is_invalid_model_error(exc: Exception) -> bool:
    """Return True when the error is specifically an invalid/unknown model name."""
    if isinstance(exc, genai_errors.ClientError):
        return exc.status_code == 404
    return False


class GoogleVisionProvider:
    """Analyzes product media using a Google Gemini vision model."""

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = settings.google_vision_model or DEFAULT_MODEL

    async def analyze(
        self,
        product_image: str,
        reference_image: str | None = None,
        video_frames: list[str] | None = None,
        model_thumbnails: list[str] | None = None,
    ) -> dict[str, Any]:
        """Analyze product media using the configured Gemini vision model."""
        contents = self._build_contents(
            product_image, reference_image, video_frames, model_thumbnails
        )

        model_to_use = self.model
        try:
            response = await self.client.aio.models.generate_content(
                model=model_to_use,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    max_output_tokens=2000,
                ),
            )
        except Exception as e:
            if _is_invalid_model_error(e) and model_to_use != DEFAULT_MODEL:
                logger.warning(
                    f"Google model '{model_to_use}' is invalid, retrying with default '{DEFAULT_MODEL}'"
                )
                model_to_use = DEFAULT_MODEL
                response = await self.client.aio.models.generate_content(
                    model=model_to_use,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        max_output_tokens=2000,
                    ),
                )
            else:
                logger.error(f"Google Gemini API error: {e}")
                raise

        text = response.text
        profile = self._parse_response(text)
        profile["provider_used"] = "google"
        profile["model_used"] = model_to_use
        profile["analysis_completeness"] = self._calculate_completeness(
            product_image, reference_image, video_frames, model_thumbnails
        )
        return profile

    def _build_contents(
        self,
        product_image: str,
        reference_image: str | None,
        video_frames: list[str] | None,
        model_thumbnails: list[str] | None,
    ) -> list:
        """Build the multimodal contents list for Gemini."""
        parts = []

        parts.append(self._data_uri_to_part(product_image, "Product image"))

        if reference_image:
            parts.append(self._data_uri_to_part(reference_image, "Reference/style image"))

        if video_frames:
            for i, frame in enumerate(video_frames[:5]):
                parts.append(self._data_uri_to_part(frame, f"Video frame {i+1}"))

        if model_thumbnails:
            for i, thumbnail in enumerate(model_thumbnails[:4]):
                parts.append(self._data_uri_to_part(thumbnail, f"3D model view {i+1}"))

        parts.append(
            types.Part.from_text(
                text=self._get_analysis_prompt(
                    reference_image is not None,
                    bool(video_frames),
                    bool(model_thumbnails),
                )
            )
        )

        return [types.Content(role="user", parts=parts)]

    def _data_uri_to_part(self, data_uri: str, label: str) -> types.Part:
        """Convert a base64 data URI to a Gemini Part."""
        if not data_uri.startswith("data:image/"):
            raise ValueError(f"Invalid data URI format for {label}")
        header, b64_data = data_uri.split(",", 1)
        mime_type = header.replace("data:", "").replace(";base64", "")
        raw_bytes = base64.b64decode(b64_data)
        return types.Part.from_bytes(data=raw_bytes, mime_type=mime_type)

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
        """Parse JSON response from Gemini."""
        try:
            json_start = text.find("{")
            json_end = text.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                return json.loads(text[json_start:json_end])
            raise ValueError("No JSON object found in response")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {text}")
            raise ValueError(f"Invalid JSON in response: {e}") from e

    def _calculate_completeness(
        self,
        product_image: str,
        reference_image: str | None,
        video_frames: list[str] | None,
        model_thumbnails: list[str] | None,
    ) -> float:
        score = 0.3
        if reference_image:
            score += 0.2
        if video_frames:
            score += 0.25
        if model_thumbnails:
            score += 0.25
        return min(1.0, score)
