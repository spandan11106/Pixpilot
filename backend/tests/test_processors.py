from pathlib import Path

import httpx
import pytest
from PIL import Image

from app.pipeline.processors import process_image, process_text
from app.pipeline.processors import video as video_module
from app.pipeline.processors.video import VideoProcessingError, process_video


def _make_image(path: Path, size=(2000, 1000), color=(120, 60, 30)) -> Path:
    Image.new("RGB", size, color).save(path)
    return path


# --- text ---------------------------------------------------------------


def test_process_text_strips_urls_and_zero_width():
    raw = "Buy at https://shop.example.com now​! See [docs](https://x.io/y)."
    result = process_text(raw)
    assert "http" not in result["content"]
    assert "​" not in result["content"]
    assert "docs" in result["content"]  # markdown link label kept
    assert result["metrics"]["word_count"] > 0


def test_process_text_collapses_blank_lines():
    result = process_text("a\n\n\n\n\nb")
    assert result["content"] == "a\n\nb"


# --- image --------------------------------------------------------------


def test_process_image_encodes_and_downscales(tmp_path: Path):
    img = _make_image(tmp_path / "p.png")
    result = process_image(img, max_longest_edge=1024)
    assert result["image_payload"].startswith("data:image/jpeg;base64,")
    assert result["metrics"]["original_resolution"] == "2000x1000"
    assert result["metrics"]["processed_resolution"] == "1024x512"


def test_process_image_rejects_bad_extension(tmp_path: Path):
    bad = tmp_path / "f.gif"
    bad.write_bytes(b"x")
    with pytest.raises(ValueError):
        process_image(bad)


def test_process_image_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        process_image(tmp_path / "nope.jpg")


# --- video --------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self) -> dict:
        return self._json


class _FakeClient:
    def __init__(self, response=None, exc=None, **_kwargs):
        self._response = response
        self._exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False

    async def post(self, _url, json=None):
        if self._exc is not None:
            raise self._exc
        return self._response


def _patch_client(monkeypatch, *, response=None, exc=None):
    monkeypatch.setattr(
        video_module.httpx,
        "AsyncClient",
        lambda **kw: _FakeClient(response=response, exc=exc, **kw),
    )


async def test_process_video_extracts_and_deletes_raw(tmp_path: Path, monkeypatch):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake-video-bytes")
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    frame_paths = []
    for i in range(3):
        fp = frames_dir / f"frame_{i:04d}.jpg"
        _make_image(fp, size=(800, 600))
        frame_paths.append(str(fp))

    _patch_client(
        monkeypatch,
        response=_FakeResponse(200, {"frame_paths": frame_paths, "frame_count": 3}),
    )

    result = await process_video(video, "http://ffmpeg:8001")
    assert result["metrics"]["frame_count"] == 3
    assert result["metrics"]["raw_video_deleted"] is True
    assert not video.exists()  # raw video deleted
    assert all(f["image_payload"].startswith("data:image/jpeg;base64,") for f in result["frames"])


async def test_process_video_empty_frames_raises(tmp_path: Path, monkeypatch):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"x")
    _patch_client(monkeypatch, response=_FakeResponse(200, {"frame_paths": []}))
    with pytest.raises(VideoProcessingError):
        await process_video(video, "http://ffmpeg:8001")
    assert video.exists()  # not deleted on failure


async def test_process_video_sidecar_error_status(tmp_path: Path, monkeypatch):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"x")
    _patch_client(monkeypatch, response=_FakeResponse(422, text="bad codec"))
    with pytest.raises(VideoProcessingError):
        await process_video(video, "http://ffmpeg:8001")


async def test_process_video_unreachable(tmp_path: Path, monkeypatch):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"x")
    _patch_client(monkeypatch, exc=httpx.ConnectError("refused"))
    with pytest.raises(VideoProcessingError):
        await process_video(video, "http://ffmpeg:8001")
