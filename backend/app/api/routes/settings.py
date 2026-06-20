from typing import Any

from dotenv import set_key
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.settings import Settings, settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

_API_KEY_FIELDS = {
    "openai_api_key",
    "anthropic_api_key",
    "google_api_key",
    "fal_api_key",
    "serpapi_api_key",
}

# Mapping from API field name → env var name (only non-trivial ones needed)
_FIELD_TO_ENV = {
    "vision_priority": "VISION_MODELS",
    "openai_api_key": "OPENAI_API_KEY",
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "google_api_key": "GOOGLE_API_KEY",
    "fal_api_key": "FAL_API_KEY",
    "serpapi_api_key": "SERPAPI_API_KEY",
    "openai_vision_model": "OPENAI_VISION_MODEL",
    "anthropic_vision_model": "ANTHROPIC_VISION_MODEL",
    "google_vision_model": "GOOGLE_VISION_MODEL",
    "summary_model": "SUMMARY_MODEL",
    "prompt_model": "PROMPT_MODEL",
}


def _mask_key(value: str) -> str:
    """Return a masked version of an API key for display."""
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return value[:4] + "..." + value[-4:]


def _build_response() -> dict[str, str]:
    return {
        "openai_api_key": _mask_key(settings.openai_api_key),
        "anthropic_api_key": _mask_key(settings.anthropic_api_key),
        "google_api_key": _mask_key(settings.google_api_key),
        "fal_api_key": _mask_key(settings.fal_api_key),
        "serpapi_api_key": _mask_key(settings.serpapi_api_key),
        "openai_vision_model": settings.openai_vision_model,
        "anthropic_vision_model": settings.anthropic_vision_model,
        "google_vision_model": settings.google_vision_model,
        "summary_model": settings.summary_model,
        "prompt_model": settings.prompt_model,
        "vision_priority": settings.vision_models,
    }


class SettingsPatch(BaseModel, extra="forbid"):
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    fal_api_key: str | None = None
    serpapi_api_key: str | None = None
    openai_vision_model: str | None = None
    anthropic_vision_model: str | None = None
    google_vision_model: str | None = None
    summary_model: str | None = None
    prompt_model: str | None = None
    vision_priority: str | None = None


@router.get("")
async def get_settings() -> dict[str, str]:
    return _build_response()


@router.patch("")
async def patch_settings(body: SettingsPatch) -> dict[str, Any]:
    dotenv_path: str = settings.model_config.get("env_file", ".env")

    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        env_key = _FIELD_TO_ENV[field]
        set_key(dotenv_path, env_key, value)

    # Reload the singleton in-place so all routes see the new values
    fresh = Settings()
    for attr in Settings.model_fields:
        object.__setattr__(settings, attr, getattr(fresh, attr))

    return {"status": "ok"}
