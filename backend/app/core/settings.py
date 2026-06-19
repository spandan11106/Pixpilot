from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    fal_api_key: str = ""
    serpapi_api_key: str = ""

    # Vision agent — provider priority and per-provider model names
    vision_models: str = "openai,anthropic,google"
    openai_vision_model: str = "gpt-4o"
    anthropic_vision_model: str = "claude-3-5-sonnet-20241022"
    google_vision_model: str = "gemini-2.0-flash"

    # Summary agent model configuration
    summary_model: str = "claude-haiku-4-5-20251001"
    prompt_model: str = "claude-sonnet-4-6"

    # Sidecar URLs
    ffmpeg_sidecar_url: str = "http://ffmpeg:8001"
    renderer_sidecar_url: str = "http://renderer:8002"

    # Storage
    content_dir: Path = Path("/app/content")

    # Server
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
