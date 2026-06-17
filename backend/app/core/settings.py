from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    fal_api_key: str = ""
    serpapi_api_key: str = ""

    # Sidecar URLs
    ffmpeg_sidecar_url: str = "http://ffmpeg:8001"
    renderer_sidecar_url: str = "http://renderer:8002"

    # Storage
    content_dir: Path = Path("/app/content")

    # Server
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
