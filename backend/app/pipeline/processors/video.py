"""Video processing for ingestion.

Delegates keyframe extraction to the FFmpeg Docker sidecar (1 FPS, max 15
frames), then runs each extracted JPG frame through the image processor to
produce base64 data URIs. The raw video is deleted after a successful
extraction (frames are all the vision pipeline needs).
"""

from pathlib import Path
from typing import Any

import httpx

from app.pipeline.processors.image import process_image

EXTRACT_FPS = 1.0
MAX_FRAMES = 15
_REQUEST_TIMEOUT = 300.0  # extraction of a 2-min video can take a while


class VideoProcessingError(RuntimeError):
    """Raised when keyframe extraction or frame processing fails."""


async def process_video(
    file_path: str | Path,
    sidecar_url: str,
    *,
    fps: float = EXTRACT_FPS,
    max_frames: int = MAX_FRAMES,
    delete_raw: bool = True,
) -> dict[str, Any]:
    """Extract keyframes via the FFmpeg sidecar and encode them as data URIs."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {path}")

    endpoint = f"{sidecar_url.rstrip('/')}/extract-frames"
    payload = {"file_path": str(path), "fps": fps, "max_frames": max_frames}

    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.post(endpoint, json=payload)
    except httpx.HTTPError as e:
        raise VideoProcessingError(f"FFmpeg sidecar unreachable: {e}") from e

    if response.status_code != 200:
        raise VideoProcessingError(
            f"FFmpeg sidecar returned {response.status_code}: {response.text}"
        )

    body = response.json()
    frame_paths = body.get("frame_paths", [])
    if not frame_paths:
        raise VideoProcessingError("FFmpeg extracted no frames from the video.")

    frames = [process_image(frame_path) for frame_path in frame_paths]

    if delete_raw:
        path.unlink(missing_ok=True)

    return {
        "status": "success",
        "filename": path.name,
        "metrics": {
            "frame_count": len(frames),
            "fps": fps,
            "raw_video_deleted": delete_raw,
        },
        "frames": frames,
    }
