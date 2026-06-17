"""FFmpeg sidecar — extracts keyframes from video files.

Stub for Milestone 0. Full implementation in Milestone 1.
"""

import shutil
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Pixpilot FFmpeg Sidecar", version="0.1.0")


class ExtractFramesRequest(BaseModel):
    file_path: str
    fps: float = 1.0
    max_frames: int = 15


class ExtractFramesResponse(BaseModel):
    frame_paths: list[str]
    frame_count: int


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/extract-frames", response_model=ExtractFramesResponse)
async def extract_frames(req: ExtractFramesRequest) -> ExtractFramesResponse:
    input_path = Path(req.file_path)
    if not input_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {req.file_path}")

    output_dir = input_path.parent / "frames"
    # Clear any frames left over from a previous extraction so the glob below
    # only returns frames produced by this run.
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = str(output_dir / "frame_%04d.jpg")

    cmd = [
        "ffmpeg", "-i", str(input_path),
        "-vf", f"fps={req.fps}",
        "-frames:v", str(req.max_frames),
        "-q:v", "2",
        output_pattern,
        "-y",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(status_code=422, detail=f"FFmpeg error: {result.stderr}")

    frames = sorted(output_dir.glob("frame_*.jpg"))
    if not frames:
        raise HTTPException(
            status_code=422,
            detail="No frames extracted; the video may be empty or an unsupported codec.",
        )
    return ExtractFramesResponse(
        frame_paths=[str(f) for f in frames],
        frame_count=len(frames),
    )
