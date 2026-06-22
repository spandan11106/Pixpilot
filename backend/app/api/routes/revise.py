"""Revision endpoint — POST /api/runs/{run_id}/revise
   Image serving   — GET  /api/runs/{run_id}/images/{filename}
"""

from __future__ import annotations

import json
import logging
import mimetypes
import re
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.run_manager import run_manager
from app.core.settings import settings
from app.pipeline.agents.image_designer import generate_image, rewrite_prompt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/runs", tags=["revise"])

_UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
MAX_ITERATIONS = 10


def _validate_run_dir(run_id: str) -> Path:
    if not _UUID4_RE.match(run_id):
        raise HTTPException(status_code=404, detail="Run not found.")
    run_dir = (settings.content_dir / run_id).resolve()
    if not run_dir.is_relative_to(settings.content_dir.resolve()) or not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found.")
    return run_dir


class ReviseRequest(BaseModel):
    feedback: str
    iteration: int


@router.post("/{run_id}/revise")
async def revise_image(run_id: str, body: ReviseRequest) -> dict:
    run_dir = _validate_run_dir(run_id)

    try:
        metadata = run_manager.get_metadata(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found.")

    image_iterations = metadata.get("image_iterations", [])
    if not image_iterations:
        raise HTTPException(status_code=400, detail="No image iterations found for this run.")

    current_iteration = image_iterations[-1]["iteration"]
    if current_iteration >= MAX_ITERATIONS:
        raise HTTPException(status_code=400, detail="max_iterations_reached")

    last_prompt = image_iterations[-1]["prompt"]
    product_profile = metadata.get("agent_states", {}).get("product_profile") or {}

    ingestion_path = run_dir / "processed" / "ingestion.json"
    if not ingestion_path.exists():
        raise HTTPException(status_code=400, detail="Ingestion data not available.")
    ingestion = json.loads(ingestion_path.read_text())
    image_data_uri = ingestion.get("image", {}).get("image_payload", "")
    if not image_data_uri:
        raise HTTPException(status_code=400, detail="Product image payload not found.")

    steering = metadata.get("steering") or {}
    aspect_ratio = steering.get("aspect_ratio") or "1:1"
    negative_prompts = steering.get("negative_prompts") or ""

    try:
        revised_prompt = await rewrite_prompt(last_prompt, body.feedback, product_profile)
    except Exception as e:
        logger.error(f"Refinement agent failed for run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Refinement agent error: {e}") from e

    try:
        fal_result = await generate_image(
            prompt=revised_prompt,
            image_data_uri=image_data_uri,
            aspect_ratio=aspect_ratio,
            negative_prompts=negative_prompts,
        )
    except Exception as e:
        logger.error(f"Image generation failed for run {run_id} revision: {e}")
        raise HTTPException(status_code=500, detail=f"Image generation error: {e}") from e

    new_iteration = current_iteration + 1
    output_filename = f"v{new_iteration}.png"
    output_path = run_dir / output_filename

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(fal_result["image_url"])
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
    except Exception as e:
        logger.error(f"Failed to save revised image for run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save image: {e}") from e

    new_entry = {
        "iteration": new_iteration,
        "prompt": revised_prompt,
        "seed": fal_result.get("seed"),
        "output_path": output_filename,
        "feedback": body.feedback,
    }
    run_manager.update_metadata(
        run_id, {"image_iterations": image_iterations + [new_entry]}
    )

    return {
        "iteration": new_iteration,
        "image_path": output_filename,
        "image_url": f"/api/runs/{run_id}/images/{output_filename}",
        "prompt_used": revised_prompt,
        "seed": fal_result.get("seed"),
    }


@router.get("/{run_id}/images/{filename}")
async def serve_image(run_id: str, filename: str) -> FileResponse:
    run_dir = _validate_run_dir(run_id)

    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file extension.")

    file_path = (run_dir / filename).resolve()
    if not file_path.is_relative_to(run_dir):
        raise HTTPException(status_code=400, detail="Invalid filename.")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found.")

    media_type = mimetypes.guess_type(file_path.name)[0] or "image/png"
    return FileResponse(file_path, media_type=media_type)
