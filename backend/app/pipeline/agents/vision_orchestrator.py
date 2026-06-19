"""Vision orchestrator that manages fallback between multiple vision providers."""

import logging
from typing import Any

from app.core.settings import settings
from app.pipeline.agents.providers.anthropic_provider import AnthropicVisionProvider
from app.pipeline.agents.providers.google_provider import GoogleVisionProvider
from app.pipeline.agents.providers.openai_provider import OpenAIVisionProvider

logger = logging.getLogger(__name__)


class VisionOrchestrator:
    """Manages fallback between vision providers in priority order."""

    def __init__(self):
        self.providers = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize available providers based on API keys."""
        if settings.openai_api_key:
            self.providers["openai"] = OpenAIVisionProvider(settings.openai_api_key)

        if settings.anthropic_api_key:
            self.providers["anthropic"] = AnthropicVisionProvider(settings.anthropic_api_key)

        if settings.google_api_key:
            self.providers["google"] = GoogleVisionProvider(settings.google_api_key)

    def get_priority_order(self) -> list[str]:
        """Get the priority order of providers from settings."""
        priority = settings.vision_models.split(",")
        return [p.strip() for p in priority if p.strip() in self.providers]

    async def analyze(
        self,
        product_image: str,
        reference_image: str | None = None,
        video_frames: list[str] | None = None,
        model_thumbnails: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Try vision providers in fallback order until one succeeds.

        Returns:
            Product profile dict from first successful provider, or None if all fail.
        """
        priority = self.get_priority_order()

        if not priority:
            logger.error("No vision providers configured with API keys")
            return None

        for provider_name in priority:
            try:
                logger.info(f"Attempting vision analysis with {provider_name}")
                provider = self.providers[provider_name]
                profile = await provider.analyze(
                    product_image, reference_image, video_frames, model_thumbnails
                )
                logger.info(f"Vision analysis succeeded with {provider_name}")
                return profile
            except Exception as e:
                logger.warning(
                    f"Vision analysis failed with {provider_name}: {e}. Trying next provider..."
                )
                continue

        logger.error("All vision providers failed")
        return None


_orchestrator: VisionOrchestrator | None = None


def get_orchestrator() -> VisionOrchestrator:
    """Return the singleton orchestrator, initializing it on first call."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = VisionOrchestrator()
    return _orchestrator


orchestrator = get_orchestrator
