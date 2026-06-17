from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.core.run_manager import run_manager
from app.core.settings import settings

router = APIRouter(prefix="/api/runs", tags=["runs"])

PipelineMode = Literal["summarize", "ecommerce", "social", "ab", "seasonal"]

SeasonalTheme = Literal[
    "Christmas", "Halloween", "Summer", "Spring", "Diwali",
    "Black Friday", "Valentine's Day", "Eid", "Hanukkah", "New Year",
]

LogoPlacement = Literal[
    "top-left", "top-right", "bottom-left", "bottom-right", "center-watermark"
]


class SteeringParams(BaseModel):
    aspect_ratio: Literal["1:1", "9:16", "16:9", "4:5"] = "1:1"
    camera_perspective: Literal[
        "Studio Eye-Level", "Flat Lay (Top-Down)", "Close-Up Macro",
        "Dynamic 3/4 View", "Hero Shot (Low Angle)",
    ] = "Studio Eye-Level"
    lighting_preset: Literal[
        "Studio Softlight", "Natural Sunshine", "Golden Hour Warmth",
        "Moody / Chiaroscuro", "Neon / Cyberpunk", "Minimalist Pastel",
    ] = "Studio Softlight"
    negative_prompts: str = ""


class SupervisionSettings(BaseModel):
    research: bool = True
    image_gen: bool = True


class SubmitPayload(BaseModel):
    description_product: Annotated[str, Field(min_length=1)]
    description_audience: Annotated[str, Field(min_length=1)]
    description_colors: Annotated[str, Field(min_length=1)]

    product_image_token: str
    video_token: str | None = None
    model_3d_token: str | None = None
    reference_image_token: str | None = None
    logo_token: str | None = None
    logo_placement: LogoPlacement = "bottom-left"

    steering: SteeringParams = SteeringParams()
    pipeline_mode: PipelineMode = "ecommerce"
    ecommerce_image_count: int = 5
    social_research_enabled: bool = False
    ab_concept_directions: str = ""
    seasonal_theme: SeasonalTheme | None = None
    supervision: SupervisionSettings = SupervisionSettings()

    @model_validator(mode="after")
    def validate_mode_fields(self) -> "SubmitPayload":
        if self.pipeline_mode == "ecommerce":
            if not (5 <= self.ecommerce_image_count <= 12):
                raise ValueError("ecommerce_image_count must be between 5 and 12")
        if self.pipeline_mode == "seasonal" and self.seasonal_theme is None:
            raise ValueError("seasonal_theme is required when pipeline_mode is 'seasonal'")
        return self


class CreateRunResponse(BaseModel):
    run_id: str


def _resolve_token(token: str | None, label: str) -> Path | None:
    if token is None:
        return None
    token_dir = settings.content_dir / "uploads" / token
    if not token_dir.exists():
        raise HTTPException(
            status_code=422,
            detail=f"Invalid token for {label}: '{token}' not found.",
        )
    files = list(token_dir.iterdir())
    if not files:
        raise HTTPException(
            status_code=422,
            detail=f"Token directory for {label} is empty.",
        )
    return files[0]


@router.post("", response_model=CreateRunResponse, status_code=201)
async def create_run() -> CreateRunResponse:
    run_id = run_manager.create_run()
    return CreateRunResponse(run_id=run_id)


@router.get("/{run_id}/metadata")
async def get_run_metadata(run_id: str) -> dict:
    return run_manager.get_metadata(run_id)


@router.post("/submit", response_model=CreateRunResponse, status_code=201)
async def submit_run(payload: SubmitPayload) -> CreateRunResponse:
    product_image_path = _resolve_token(payload.product_image_token, "product_image")
    if product_image_path is None:
        raise HTTPException(status_code=422, detail="product_image_token is required.")

    file_map: dict[str, Path] = {"product_image": product_image_path}
    optional_tokens = {
        "video": payload.video_token,
        "model_3d": payload.model_3d_token,
        "reference_image": payload.reference_image_token,
        "logo": payload.logo_token,
    }
    for field, token in optional_tokens.items():
        path = _resolve_token(token, field)
        if path is not None:
            file_map[field] = path

    run_id = run_manager.create_run_from_submission(
        payload=payload.model_dump(),
        file_map=file_map,
    )
    return CreateRunResponse(run_id=run_id)
