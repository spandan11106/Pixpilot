import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.core.settings import settings

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

FileType = Literal["product_image", "reference_image", "video", "model_3d"]

_RULES: dict[str, dict] = {
    "product_image":   {"exts": {"jpg", "jpeg", "png", "webp"}, "max_mb": 20},
    "reference_image": {"exts": {"jpg", "jpeg", "png", "webp"}, "max_mb": 20},
    "video":           {"exts": {"mp4", "mov", "webm"}, "max_mb": 100},
    "model_3d":        {"exts": {"gltf", "glb", "obj", "usdz", "zip"}, "max_mb": 50},
}


class UploadResponse(BaseModel):
    upload_token: str


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
