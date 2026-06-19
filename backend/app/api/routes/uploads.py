import json
import re
import shutil
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.core.settings import settings
from app.pipeline.processors import process_image, process_model, process_video

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

FileType = Literal["product_image", "reference_image", "video", "model_3d"]

_RULES: dict[str, dict] = {
    "product_image":   {"exts": {"jpg", "jpeg", "png", "webp"}, "max_mb": 20},
    "reference_image": {"exts": {"jpg", "jpeg", "png", "webp"}, "max_mb": 20},
    "video":           {"exts": {"mp4", "mov", "webm"}, "max_mb": 100},
    "model_3d":        {"exts": {"gltf", "glb", "obj", "usdz", "zip"}, "max_mb": 50},
}

# Perspective order the renderer sidecar emits its thumbnails in.
_VIEW_LABELS = ["Front", "3/4 View", "Side", "Back"]

_UUID4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


class UploadResponse(BaseModel):
    upload_token: str


class PreviewItem(BaseModel):
    url: str
    label: str


class Preview(BaseModel):
    kind: Literal["image", "frames", "views"]
    items: list[PreviewItem]


class ProcessResponse(BaseModel):
    status: Literal["success", "error"]
    file_type: str
    preview: Preview | None = None
    error: str | None = None


def _token_dir(token: str) -> Path:
    """Resolve and validate a token's upload directory (path-traversal safe)."""
    if not _UUID4_RE.match(token):
        raise HTTPException(status_code=422, detail="Invalid token format.")
    uploads_root = (settings.content_dir / "uploads").resolve()
    token_dir = (uploads_root / token).resolve()
    if not token_dir.is_relative_to(uploads_root):
        raise HTTPException(status_code=422, detail="Invalid token.")
    if not token_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Upload '{token}' not found.")
    return token_dir


def _token_file(token_dir: Path) -> Path:
    """Return the single raw upload inside a token dir (ignores cache/extracts)."""
    files = [
        p
        for p in token_dir.iterdir()
        if p.is_file() and p.name != "processed.json"
    ]
    if not files:
        raise HTTPException(status_code=404, detail="Upload file missing.")
    return files[0].resolve()


@router.post("", response_model=UploadResponse)
async def upload_file(
    file_type: FileType = Query(...),
    file: UploadFile = File(...),
) -> UploadResponse:
    rule = _RULES[file_type]
    ext = Path(file.filename or "").suffix.lstrip(".").lower()
    if ext not in rule["exts"]:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid extension '.{ext}' for {file_type}. "
                   f"Accepted: {sorted(rule['exts'])}",
        )

    content = await file.read()
    max_bytes = rule["max_mb"] * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=422,
            detail=f"File size {len(content)} bytes exceeds {rule['max_mb']}MB size limit.",
        )

    token = str(uuid.uuid4())
    dest_dir: Path = settings.content_dir / "uploads" / token
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "upload").name or "upload"
    (dest_dir / safe_name).write_bytes(content)

    return UploadResponse(upload_token=token)


@router.post("/{token}/process", response_model=ProcessResponse)
async def process_upload(
    token: str,
    file_type: FileType = Query(...),
) -> ProcessResponse:
    """Run the matching processor on a staged upload right away.

    The full processor result is cached to ``<token>/processed.json`` so the run
    can reuse it instead of re-invoking the sidecars. The raw file is kept
    (``delete_raw=False``) so the run can still move it into ``inputs/``. The
    response carries a lean, preview-shaped payload for the upload UI.
    """
    token_dir = _token_dir(token)
    file_path = _token_file(token_dir)

    try:
        if file_type in ("product_image", "reference_image"):
            result = process_image(file_path)
            preview = Preview(
                kind="image",
                items=[PreviewItem(url=result["image_payload"], label="Preview")],
            )
        elif file_type == "video":
            result = await process_video(
                file_path, settings.ffmpeg_sidecar_url, delete_raw=False
            )
            preview = Preview(
                kind="frames",
                items=[
                    PreviewItem(url=f["image_payload"], label=f"Frame {i + 1}")
                    for i, f in enumerate(result["frames"])
                ],
            )
        else:  # model_3d
            result = await process_model(
                file_path, settings.renderer_sidecar_url, delete_raw=False
            )
            preview = Preview(
                kind="views",
                items=[
                    PreviewItem(
                        url=t["image_payload"],
                        label=_VIEW_LABELS[i] if i < len(_VIEW_LABELS) else f"View {i + 1}",
                    )
                    for i, t in enumerate(result["thumbnails"])
                ],
            )
    except Exception as e:  # noqa: BLE001 - surface any processing failure to the UI
        return ProcessResponse(status="error", file_type=file_type, error=str(e))

    cache = {"status": "success", "file_type": file_type, "result": result}
    (token_dir / "processed.json").write_text(json.dumps(cache))

    return ProcessResponse(status="success", file_type=file_type, preview=preview)


@router.delete("/{token}", status_code=204)
async def delete_upload(token: str) -> None:
    """Remove a staged upload (raw file + cached processing) from disk."""
    token_dir = _token_dir(token)
    shutil.rmtree(token_dir, ignore_errors=True)
