"""Summary Agent — two sequential LLM calls.

Call 1 (summary_model):  product_profile + user description → Input Summary Card JSON
Call 2 (prompt_model):   summary_card + steering params    → structured Image Gen Prompt JSON

If the Vision Agent produced no product_profile the agent proceeds with text-only
inputs and marks vision_available=False in the summary card.
"""

import json
import logging
from typing import Any

import anthropic

from app.core.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_SUMMARY_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_PROMPT_MODEL = "claude-sonnet-4-6"


def _is_invalid_model_error(exc: anthropic.APIError) -> bool:
    if isinstance(exc, anthropic.NotFoundError):
        return True
    if isinstance(exc, anthropic.BadRequestError):
        msg = str(exc).lower()
        return "model" in msg and ("not found" in msg or "invalid" in msg or "does not exist" in msg)
    return False


_SUMMARY_CARD_SCHEMA = """{
  "product_name": "inferred short product name",
  "product_category": "e.g. cosmetic bottle, furniture, apparel",
  "key_features": ["feature 1", "feature 2"],
  "target_audience": "description of the target audience",
  "dominant_colors": ["#hex1", "#hex2"],
  "materials": ["material 1", "material 2"],
  "style_vibe": "overall aesthetic vibe in 2–4 words",
  "vision_available": true
}"""

_IMAGE_PROMPT_SCHEMA = """{
  "subject": "precise description of the product and its physical details",
  "style": "photography/art style and overall aesthetic",
  "lighting": "specific lighting description",
  "background": "background and surface description",
  "composition": "framing and compositional notes",
  "color_palette": "color direction for the scene",
  "camera_angle": "passthrough from steering",
  "aspect_ratio": "passthrough from steering",
  "negative_prompts": "passthrough from steering",
  "lighting_preset": "passthrough from steering"
}"""


def _make_client() -> anthropic.AsyncAnthropic:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured.")
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


async def generate_summary_card(
    text_results: dict[str, Any],
    product_profile: dict[str, Any] | None,
) -> dict[str, Any]:
    """Call 1: merge vision profile + user description into an Input Summary Card."""
    client = _make_client()

    vision_section = (
        json.dumps(product_profile, indent=2)
        if product_profile
        else "Not available — vision analysis was skipped or failed."
    )

    prompt = f"""You are a product analyst. Merge the following inputs into a concise, structured product summary.

## User Description
- Product Info: {text_results.get('product', {}).get('text', '')}
- Target Audience: {text_results.get('audience', {}).get('text', '')}
- Desired Colors: {text_results.get('colors', {}).get('text', '')}

## Vision Analysis
{vision_section}

Produce a JSON object matching this exact schema:
{_SUMMARY_CARD_SCHEMA}

Set "vision_available" to {str(product_profile is not None).lower()}.
Return ONLY valid JSON, no additional text."""

    model_to_use = settings.summary_model or DEFAULT_SUMMARY_MODEL
    try:
        response = await client.messages.create(
            model=model_to_use,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as e:
        if _is_invalid_model_error(e) and model_to_use != DEFAULT_SUMMARY_MODEL:
            logger.warning(
                f"Summary model '{model_to_use}' is invalid, retrying with default '{DEFAULT_SUMMARY_MODEL}'"
            )
            model_to_use = DEFAULT_SUMMARY_MODEL
            response = await client.messages.create(
                model=model_to_use,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )
        else:
            raise

    text = response.content[0].text
    return _parse_json(text, "summary card")


async def generate_image_prompt(
    summary_card: dict[str, Any],
    steering: dict[str, Any],
) -> dict[str, Any]:
    """Call 2: turn summary card + steering params into a structured image generation prompt."""
    client = _make_client()

    prompt = f"""You are a creative director specialising in AI image generation prompts.
Given the product summary below, craft a structured image generation prompt optimised
for a photorealistic product image generator (FLUX / Stable Diffusion).

## Product Summary
{json.dumps(summary_card, indent=2)}

## User Steering Parameters (pass these through exactly as given)
- Aspect Ratio: {steering.get('aspect_ratio', '1:1')}
- Camera Perspective: {steering.get('camera_perspective', 'Studio Eye-Level')}
- Lighting Preset: {steering.get('lighting_preset', 'Studio Softlight')}
- Negative Prompts: {steering.get('negative_prompts', '')}

Produce a JSON object matching this exact schema:
{_IMAGE_PROMPT_SCHEMA}

Rules:
- "subject" must describe the physical product accurately based on the summary.
- "style", "lighting", "background", "composition", "color_palette" should be rich,
  specific, and optimised for photorealistic generation — avoid vague words like "nice".
- Copy the steering fields verbatim into their corresponding keys.
Return ONLY valid JSON, no additional text."""

    model_to_use = settings.prompt_model or DEFAULT_PROMPT_MODEL
    try:
        response = await client.messages.create(
            model=model_to_use,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as e:
        if _is_invalid_model_error(e) and model_to_use != DEFAULT_PROMPT_MODEL:
            logger.warning(
                f"Prompt model '{model_to_use}' is invalid, retrying with default '{DEFAULT_PROMPT_MODEL}'"
            )
            model_to_use = DEFAULT_PROMPT_MODEL
            response = await client.messages.create(
                model=model_to_use,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )
        else:
            raise

    text = response.content[0].text
    result = _parse_json(text, "image prompt")

    # Guarantee steering passthrough even if model omitted them
    result.setdefault("camera_angle", steering.get("camera_perspective", "Studio Eye-Level"))
    result.setdefault("aspect_ratio", steering.get("aspect_ratio", "1:1"))
    result.setdefault("negative_prompts", steering.get("negative_prompts", ""))
    result.setdefault("lighting_preset", steering.get("lighting_preset", "Studio Softlight"))

    return result


def _parse_json(text: str, label: str) -> dict[str, Any]:
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
        raise ValueError("No JSON object found")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse {label} response: {text[:500]}")
        raise ValueError(f"Invalid JSON in {label} response: {e}") from e
