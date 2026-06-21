import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from PIL import Image

from app.core.run_manager import run_manager
from app.pipeline import graph
from app.pipeline.graph import run_pipeline


def _make_run(
    tmp_content_dir: Path,
    *,
    with_image=True,
    with_video=False,
    with_model=False,
    with_reference=False,
) -> str:
    run_id = run_manager.create_run()
    inputs_dir = tmp_content_dir / run_id / "inputs"
    inputs = {
        "description_product": "Argan oil, 30ml amber bottle. https://shop.example.com",
        "description_audience": "Women 28-45, natural skincare.",
        "description_colors": "Cream, matte gold.",
        "image_path": None,
        "video_path": None,
        "model_3d_path": None,
        "reference_image_path": None,
    }
    if with_image:
        img = inputs_dir / "product_image_p.jpg"
        Image.new("RGB", (1500, 1500), (200, 180, 140)).save(img)
        inputs["image_path"] = "inputs/product_image_p.jpg"
    if with_video:
        (inputs_dir / "video_clip.mp4").write_bytes(b"fake")
        inputs["video_path"] = "inputs/video_clip.mp4"
    if with_model:
        (inputs_dir / "model_3d_chair.glb").write_bytes(b"fake")
        inputs["model_3d_path"] = "inputs/model_3d_chair.glb"
    if with_reference:
        ref = inputs_dir / "reference_image_r.png"
        Image.new("RGB", (1200, 900), (60, 90, 160)).save(ref)
        inputs["reference_image_path"] = "inputs/reference_image_r.png"
    run_manager.update_metadata(run_id, {"inputs": inputs})
    return run_id


async def _collect(run_id: str) -> list[dict]:
    return [event async for event in run_pipeline(run_id)]


_FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
_FAKE_FAL_RESULT = {
    "images": [{"url": "https://fal.media/files/out.jpg"}],
    "seed": 1,
}
_FAKE_BLUEPRINT = {
    "subject": "bottle",
    "style": "photo",
    "lighting": "soft",
    "background": "white",
    "composition": "center",
    "color_palette": "cream",
    "camera_angle": "eye-level",
    "aspect_ratio": "1:1",
    "negative_prompts": "",
    "lighting_preset": "Studio Softlight",
}


@contextmanager
def _image_designer_mocks():
    """Context manager that patches all image designer dependencies.

    Patches functions at the graph module's namespace (where they are imported)
    so the pipeline nodes see the mocks correctly.
    """
    with patch("app.pipeline.graph.get_orchestrator") as mock_orch, \
         patch(
             "app.pipeline.graph.generate_summary_card",
             new=AsyncMock(return_value={"product_name": "Test", "vision_available": False}),
         ), \
         patch(
             "app.pipeline.graph.generate_image_prompt",
             new=AsyncMock(return_value=_FAKE_BLUEPRINT),
         ), \
         patch("fal_client.upload", return_value="https://fal.storage/img.jpg"), \
         patch("fal_client.run_async", new=AsyncMock(return_value=_FAKE_FAL_RESULT)), \
         patch("app.pipeline.agents.image_designer.settings") as mock_img_settings, \
         patch("httpx.AsyncClient") as mock_httpx:
        mock_orch.return_value.analyze = AsyncMock(return_value=None)
        mock_img_settings.fal_api_key = "test-key"
        mock_img_settings.fal_image_model = "fal-ai/flux/dev/image-to-image"
        mock_img_settings.anthropic_api_key = "test-key"
        mock_img_settings.prompt_model = "claude-sonnet-4-6"
        mock_httpx.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock(
                get=AsyncMock(return_value=MagicMock(content=_FAKE_PNG))
            )
        )
        mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)
        yield


async def test_pipeline_text_and_image_no_video(tmp_content_dir: Path):
    run_id = _make_run(tmp_content_dir)
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20

    with patch("app.pipeline.graph.get_orchestrator") as mock_orch, \
         patch(
             "app.pipeline.graph.generate_summary_card",
             new=AsyncMock(return_value={"product_name": "Test", "vision_available": False}),
         ), \
         patch(
             "app.pipeline.graph.generate_image_prompt",
             new=AsyncMock(return_value={
                 "subject": "bottle", "style": "photo", "lighting": "soft",
                 "background": "white", "composition": "center", "color_palette": "cream",
                 "camera_angle": "eye-level", "aspect_ratio": "1:1",
                 "negative_prompts": "", "lighting_preset": "Studio Softlight",
             }),
         ), \
         patch("fal_client.upload", return_value="https://fal.storage/img.jpg"), \
         patch("fal_client.run_async", new=AsyncMock(return_value={
             "images": [{"url": "https://fal.media/out.jpg"}], "seed": 1,
         })), \
         patch("app.pipeline.agents.image_designer.settings") as mock_img_settings, \
         patch("httpx.AsyncClient") as mock_httpx:
        mock_orch.return_value.analyze = AsyncMock(return_value=None)
        mock_img_settings.fal_api_key = "test-key"
        mock_img_settings.fal_image_model = "fal-ai/flux/dev/image-to-image"
        mock_httpx.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock(get=AsyncMock(return_value=MagicMock(content=fake_png)))
        )
        mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)
        events = await _collect(run_id)

    names = [e["event"] for e in events]
    assert "pipeline_started" in names
    assert "text_processed" in names
    assert "image_processed" in names
    assert "ingestion_complete" in names
    assert "image_generation_started" in names
    assert "image_generation_complete" in names
    assert "pipeline_complete" in names

    artifact = json.loads(
        (tmp_content_dir / run_id / "processed" / "ingestion.json").read_text()
    )
    assert artifact["image"]["image_payload"].startswith("data:image/jpeg;base64,")


async def test_pipeline_with_video(tmp_content_dir: Path, monkeypatch):
    run_id = _make_run(tmp_content_dir, with_video=True)

    async def fake_process_video(path, sidecar_url, **kw):
        Path(path).unlink(missing_ok=True)
        return {
            "status": "success",
            "filename": Path(path).name,
            "metrics": {"frame_count": 12, "fps": 1.0, "raw_video_deleted": True},
            "frames": [{"metrics": {}, "image_payload": "data:image/jpeg;base64,AAAA"}],
        }

    monkeypatch.setattr(graph, "process_video", fake_process_video)

    with _image_designer_mocks():
        events = await _collect(run_id)

    names = [e["event"] for e in events]
    assert "video_processed" in names
    assert next(e for e in events if e["event"] == "video_processed")["data"]["frame_count"] == 12

    meta = run_manager.get_metadata(run_id)
    assert meta["ingestion"]["video_frame_count"] == 12
    artifact = json.loads((tmp_content_dir / run_id / "processed" / "ingestion.json").read_text())
    assert artifact["video"]["metrics"]["frame_count"] == 12


async def test_pipeline_video_failure_is_non_fatal(tmp_content_dir: Path, monkeypatch):
    run_id = _make_run(tmp_content_dir, with_video=True)

    async def boom(path, sidecar_url, **kw):
        raise RuntimeError("sidecar down")

    monkeypatch.setattr(graph, "process_video", boom)

    with _image_designer_mocks():
        events = await _collect(run_id)

    names = [e["event"] for e in events]
    assert "video_failed" in names
    assert "pipeline_complete" in names  # run still completes
    meta = run_manager.get_metadata(run_id)
    assert meta["ingestion"]["video_frame_count"] == 0


async def test_pipeline_with_model(tmp_content_dir: Path, monkeypatch):
    run_id = _make_run(tmp_content_dir, with_model=True)

    async def fake_process_model(path, sidecar_url, **kw):
        Path(path).unlink(missing_ok=True)
        return {
            "status": "success",
            "filename": Path(path).name,
            "metrics": {"thumbnail_count": 4, "raw_model_deleted": True},
            "thumbnails": [
                {"metrics": {}, "image_payload": "data:image/jpeg;base64,AAAA"}
                for _ in range(4)
            ],
        }

    monkeypatch.setattr(graph, "process_model", fake_process_model)

    with _image_designer_mocks():
        events = await _collect(run_id)

    names = [e["event"] for e in events]
    assert "model_processed" in names
    assert next(e for e in events if e["event"] == "model_processed")["data"][
        "thumbnail_count"
    ] == 4

    meta = run_manager.get_metadata(run_id)
    assert meta["ingestion"]["model_3d_thumbnail_count"] == 4
    artifact = json.loads((tmp_content_dir / run_id / "processed" / "ingestion.json").read_text())
    assert len(artifact["model_3d"]["thumbnails"]) == 4


async def test_pipeline_model_failure_is_non_fatal(tmp_content_dir: Path, monkeypatch):
    run_id = _make_run(tmp_content_dir, with_model=True)

    async def boom(path, sidecar_url, **kw):
        raise RuntimeError("unsupported format")

    monkeypatch.setattr(graph, "process_model", boom)

    with _image_designer_mocks():
        events = await _collect(run_id)

    names = [e["event"] for e in events]
    assert "model_failed" in names
    assert "pipeline_complete" in names  # run still completes
    meta = run_manager.get_metadata(run_id)
    assert meta["ingestion"]["model_3d_thumbnail_count"] == 0


async def test_pipeline_with_reference(tmp_content_dir: Path):
    run_id = _make_run(tmp_content_dir, with_reference=True)

    with _image_designer_mocks():
        events = await _collect(run_id)

    names = [e["event"] for e in events]
    assert "reference_processed" in names
    assert "reference_skipped" not in names

    artifact = json.loads((tmp_content_dir / run_id / "processed" / "ingestion.json").read_text())
    assert artifact["reference_image"]["image_payload"].startswith("data:image/jpeg;base64,")

    meta = run_manager.get_metadata(run_id)
    assert meta["ingestion"]["reference_image_processed"] is True


async def test_pipeline_reference_failure_is_non_fatal(tmp_content_dir: Path, monkeypatch):
    run_id = _make_run(tmp_content_dir, with_reference=True)

    real_process_image = graph.process_image

    def selective_boom(path, *args, **kwargs):
        if "reference_image" in Path(path).name:
            raise RuntimeError("corrupt reference")
        return real_process_image(path, *args, **kwargs)

    monkeypatch.setattr(graph, "process_image", selective_boom)

    with _image_designer_mocks():
        events = await _collect(run_id)

    names = [e["event"] for e in events]
    assert "reference_failed" in names
    assert "pipeline_complete" in names  # run still completes
    meta = run_manager.get_metadata(run_id)
    assert meta["ingestion"]["reference_image_processed"] is False


async def test_pipeline_reuses_cached_model(tmp_content_dir: Path, monkeypatch):
    """A successful upload-time cache is reused; the sidecar is never called."""
    run_id = _make_run(tmp_content_dir, with_model=True)
    cache_dir = tmp_content_dir / run_id / "processed" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "model_3d.json").write_text(
        json.dumps(
            {
                "status": "success",
                "file_type": "model_3d",
                "result": {
                    "status": "success",
                    "filename": "chair.glb",
                    "metrics": {"thumbnail_count": 4},
                    "thumbnails": [
                        {"metrics": {}, "image_payload": "data:image/jpeg;base64,AAAA"}
                        for _ in range(4)
                    ],
                },
            }
        )
    )

    async def boom(path, sidecar_url, **kw):
        raise AssertionError("renderer sidecar should not be called when cached")

    monkeypatch.setattr(graph, "process_model", boom)

    with _image_designer_mocks():
        events = await _collect(run_id)

    model_evt = next(e for e in events if e["event"] == "model_processed")
    assert model_evt["data"]["cached"] is True
    assert model_evt["data"]["thumbnail_count"] == 4
    meta = run_manager.get_metadata(run_id)
    assert meta["ingestion"]["model_3d_thumbnail_count"] == 4


async def test_pipeline_ignores_errored_cache(tmp_content_dir: Path, monkeypatch):
    """An errored cache is not reused — the node processes the input fresh."""
    run_id = _make_run(tmp_content_dir, with_model=True)
    cache_dir = tmp_content_dir / run_id / "processed" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "model_3d.json").write_text(
        json.dumps({"status": "error", "file_type": "model_3d", "error": "sidecar down"})
    )

    called = {"n": 0}

    async def fake_process_model(path, sidecar_url, **kw):
        called["n"] += 1
        Path(path).unlink(missing_ok=True)
        return {
            "status": "success",
            "filename": Path(path).name,
            "metrics": {"thumbnail_count": 4},
            "thumbnails": [{"metrics": {}, "image_payload": "data:image/jpeg;base64,AAAA"}],
        }

    monkeypatch.setattr(graph, "process_model", fake_process_model)

    with _image_designer_mocks():
        events = await _collect(run_id)

    assert called["n"] == 1  # reprocessed fresh
    model_evt = next(e for e in events if e["event"] == "model_processed")
    assert model_evt["data"]["cached"] is False


async def test_pipeline_halts_when_image_missing(tmp_content_dir: Path):
    run_id = _make_run(tmp_content_dir, with_image=False)
    events = await _collect(run_id)
    names = [e["event"] for e in events]
    assert "pipeline_error" in names
    assert "pipeline_complete" not in names  # halted
    assert "ingestion_complete" not in names
    meta = run_manager.get_metadata(run_id)
    assert meta["status"] == "failed"


async def test_pipeline_image_generation_complete(tmp_content_dir):
    run_id = _make_run(tmp_content_dir)
    fake_fal_result = {
        "images": [{"url": "https://fal.media/files/out.jpg"}],
        "seed": 77,
    }
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20

    with patch("app.pipeline.graph.get_orchestrator") as mock_orch, \
         patch(
             "app.pipeline.graph.generate_summary_card",
             new=AsyncMock(return_value={"product_name": "Test", "vision_available": False}),
         ), \
         patch(
             "app.pipeline.graph.generate_image_prompt",
             new=AsyncMock(return_value={
                 "subject": "test bottle", "style": "editorial", "lighting": "soft",
                 "background": "white", "composition": "centered", "color_palette": "cream",
                 "camera_angle": "eye-level", "aspect_ratio": "1:1",
                 "negative_prompts": "", "lighting_preset": "Studio Softlight",
             }),
         ), \
         patch("fal_client.upload", return_value="https://fal.storage/img.jpg"), \
         patch("fal_client.run_async", new=AsyncMock(return_value=fake_fal_result)), \
         patch("app.pipeline.agents.image_designer.settings") as mock_img_settings, \
         patch("httpx.AsyncClient") as mock_httpx:
        mock_orch.return_value.analyze = AsyncMock(return_value=None)
        mock_img_settings.fal_api_key = "test-key"
        mock_img_settings.fal_image_model = "fal-ai/flux/dev/image-to-image"
        mock_img_settings.anthropic_api_key = "test-key"
        mock_img_settings.prompt_model = "claude-sonnet-4-6"
        mock_httpx.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock(get=AsyncMock(return_value=MagicMock(content=fake_png)))
        )
        mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)
        events = await _collect(run_id)

    names = [e["event"] for e in events]
    assert "image_generation_started" in names
    assert "image_generation_complete" in names
    assert "image_generation_failed" not in names

    complete = next(e for e in events if e["event"] == "image_generation_complete")
    assert complete["data"]["iteration"] == 1
    assert complete["data"]["image_path"] == "v1.png"
    assert f"/api/runs/{run_id}/images/v1.png" == complete["data"]["image_url"]

    assert (tmp_content_dir / run_id / "v1.png").exists()
    meta = run_manager.get_metadata(run_id)
    assert meta["status"] == "image_generated"
    assert len(meta["image_iterations"]) == 1


async def test_pipeline_image_generation_failed_routes_to_end(tmp_content_dir):
    run_id = _make_run(tmp_content_dir)

    with patch("app.pipeline.graph.get_orchestrator") as mock_orch, \
         patch(
             "app.pipeline.graph.generate_summary_card",
             new=AsyncMock(return_value={"product_name": "Test", "vision_available": False}),
         ), \
         patch(
             "app.pipeline.graph.generate_image_prompt",
             new=AsyncMock(return_value={
                 "subject": "bottle", "style": "photo", "lighting": "soft",
                 "background": "white", "composition": "center", "color_palette": "cream",
                 "camera_angle": "eye-level", "aspect_ratio": "1:1",
                 "negative_prompts": "", "lighting_preset": "Studio Softlight",
             }),
         ), \
         patch("fal_client.upload", return_value="https://fal.storage/img.jpg"), \
         patch("fal_client.run_async", new=AsyncMock(side_effect=RuntimeError("fal down"))), \
         patch("asyncio.sleep", new=AsyncMock()), \
         patch("app.pipeline.agents.image_designer.settings") as mock_img_settings:
        mock_orch.return_value.analyze = AsyncMock(return_value=None)
        mock_img_settings.fal_api_key = "test-key"
        mock_img_settings.fal_image_model = "fal-ai/flux/dev/image-to-image"
        mock_img_settings.anthropic_api_key = "test-key"
        mock_img_settings.prompt_model = "claude-sonnet-4-6"
        events = await _collect(run_id)

    names = [e["event"] for e in events]
    assert "image_generation_failed" in names
    assert "pipeline_complete" not in names
