"""Vision provider interface for multimodal product analysis.

Each provider (OpenAI, Anthropic, Google) implements this interface to analyze
product media and return a flexible product profile dict.
"""

from typing import Any, Protocol


class VisionProvider(Protocol):
    """Interface for vision models that analyze product media."""

    async def analyze(
        self,
        product_image: str,
        reference_image: str | None = None,
        video_frames: list[str] | None = None,
        model_thumbnails: list[str] | None = None,
    ) -> dict[str, Any]:
        """Analyze media and return a flexible product profile dict.

        Args:
            product_image: Base64 data URI of the product image (required)
            reference_image: Base64 data URI of reference style image (optional)
            video_frames: List of base64 data URIs from video keyframes (optional)
            model_thumbnails: List of base64 data URIs from 3D model renders (optional)

        Returns:
            dict with at minimum:
            - product_category: str
            - dominant_colors: list[str]
            - materials_textures: list[str]
            - usps: list[str]
            - product_shape: str
            - provider_used: str
            - analysis_completeness: float (0.0-1.0)

            May also include optional fields:
            - inferred_style_from_reference: dict | None
            - lighting_conditions: str | None
            - surface_finish: str | None
            - scale_proportion: str | None
        """
        ...
