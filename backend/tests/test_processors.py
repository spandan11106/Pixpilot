from pathlib import Path

import httpx
import pytest
from PIL import Image

from app.pipeline.processors import model as model_module
from app.pipeline.processors import process_image, process_text
from app.pipeline.processors import video as video_module
from app.pipeline.processors.model import ModelProcessingError, process_model
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


# --- 3D model -----------------------------------------------------------


def _patch_model_client(monkeypatch, *, response=None, exc=None):
    monkeypatch.setattr(
        model_module.httpx,
        "AsyncClient",
        lambda **kw: _FakeClient(response=response, exc=exc, **kw),
    )


async def test_process_model_renders_and_deletes_raw(tmp_path: Path, monkeypatch):
    model = tmp_path / "chair.glb"
    model.write_bytes(b"fake-glb-bytes")
    renders_dir = tmp_path / "renders"
    renders_dir.mkdir()
    thumbnails = []
    for name in ("front", "three_quarter", "side", "back"):
        fp = renders_dir / f"{name}.png"
        _make_image(fp, size=(1024, 1024))
        thumbnails.append(str(fp))

    _patch_model_client(
        monkeypatch,
        response=_FakeResponse(
            200, {"thumbnails": thumbnails, "metrics": {"vertex_count": 100}}
        ),
    )

    result = await process_model(model, "http://renderer:8002")
    assert result["metrics"]["thumbnail_count"] == 4
    assert result["metrics"]["raw_model_deleted"] is True
    assert result["metrics"]["vertex_count"] == 100
    assert not model.exists()  # raw model deleted
    assert all(
        t["image_payload"].startswith("data:image/jpeg;base64,")
        for t in result["thumbnails"]
    )


async def test_process_model_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        await process_model(tmp_path / "nope.glb", "http://renderer:8002")


async def test_process_model_empty_thumbnails_raises(tmp_path: Path, monkeypatch):
    model = tmp_path / "chair.glb"
    model.write_bytes(b"x")
    _patch_model_client(monkeypatch, response=_FakeResponse(200, {"thumbnails": []}))
    with pytest.raises(ModelProcessingError):
        await process_model(model, "http://renderer:8002")
    assert model.exists()  # not deleted on failure


async def test_process_model_unsupported_format_raises(tmp_path: Path, monkeypatch):
    model = tmp_path / "chair.usdz"
    model.write_bytes(b"x")
    _patch_model_client(
        monkeypatch, response=_FakeResponse(400, text="unsupported format: usdz")
    )
    with pytest.raises(ModelProcessingError):
        await process_model(model, "http://renderer:8002")
    assert model.exists()  # not deleted on failure


async def test_process_model_unreachable(tmp_path: Path, monkeypatch):
    model = tmp_path / "chair.glb"
    model.write_bytes(b"x")
    _patch_model_client(monkeypatch, exc=httpx.ConnectError("refused"))
    with pytest.raises(ModelProcessingError):
        await process_model(model, "http://renderer:8002")


# --- 3D model: zip bundles ----------------------------------------------


class _FakeRendererClient:
    """Mimics the renderer: writes 4 PNGs next to the model it is given and
    records the model_path it was asked to render."""

    received_model_path: str | None = None

    def __init__(self, **_kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False

    async def post(self, _url, json=None):
        model_path = Path(json["model_path"])
        _FakeRendererClient.received_model_path = str(model_path)
        renders = model_path.parent / "renders"
        renders.mkdir(parents=True, exist_ok=True)
        thumbs = []
        for name in ("front", "three_quarter", "side", "back"):
            fp = renders / f"{name}.png"
            _make_image(fp, size=(1024, 1024))
            thumbs.append(str(fp))
        return _FakeResponse(200, {"thumbnails": thumbs, "metrics": {}})


def _make_zip(path: Path, members: dict[str, bytes]) -> Path:
    import zipfile

    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return path


async def test_process_model_zip_extracts_and_renders_entrypoint(tmp_path, monkeypatch):
    _FakeRendererClient.received_model_path = None
    zip_path = _make_zip(
        tmp_path / "bundle.zip",
        {
            "model/scene.gltf": b'{"asset":{"version":"2.0"}}',
            "model/scene.bin": b"binary-geometry",
            "model/textures/diffuse.png": b"png-bytes",
        },
    )
    monkeypatch.setattr(
        model_module.httpx, "AsyncClient", lambda **kw: _FakeRendererClient(**kw)
    )

    result = await process_model(zip_path, "http://renderer:8002")

    # The .gltf inside the bundle is what gets rendered, not the zip.
    assert _FakeRendererClient.received_model_path.endswith("scene.gltf")
    assert result["metrics"]["thumbnail_count"] == 4
    # Bundle and extracted contents are cleaned up after success.
    assert not zip_path.exists()
    assert not (tmp_path / "bundle_extracted").exists()


async def test_process_model_zip_without_entrypoint_raises(tmp_path, monkeypatch):
    zip_path = _make_zip(
        tmp_path / "bundle.zip",
        {"textures/diffuse.png": b"png", "readme.txt": b"hi"},
    )
    monkeypatch.setattr(
        model_module.httpx, "AsyncClient", lambda **kw: _FakeRendererClient(**kw)
    )
    with pytest.raises(ModelProcessingError):
        await process_model(zip_path, "http://renderer:8002")


async def test_process_model_zip_slip_is_rejected(tmp_path, monkeypatch):
    zip_path = _make_zip(
        tmp_path / "bundle.zip",
        {"../escape.gltf": b'{"asset":{"version":"2.0"}}'},
    )
    monkeypatch.setattr(
        model_module.httpx, "AsyncClient", lambda **kw: _FakeRendererClient(**kw)
    )
    with pytest.raises(ModelProcessingError):
        await process_model(zip_path, "http://renderer:8002")
    # Nothing escaped the working directory.
    assert not (tmp_path.parent / "escape.gltf").exists()
