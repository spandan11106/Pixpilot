import json
from pathlib import Path

from PIL import Image

from app.core.run_manager import run_manager
from app.pipeline import graph
from app.pipeline.graph import run_pipeline


def _make_run(tmp_content_dir: Path, *, with_image=True, with_video=False) -> str:
    run_id = run_manager.create_run()
    inputs_dir = tmp_content_dir / run_id / "inputs"
    inputs = {
        "description_product": "Argan oil, 30ml amber bottle. https://shop.example.com",
        "description_audience": "Women 28-45, natural skincare.",
        "description_colors": "Cream, matte gold.",
        "image_path": None,
        "video_path": None,
    }
    if with_image:
        img = inputs_dir / "product_image_p.jpg"
        Image.new("RGB", (1500, 1500), (200, 180, 140)).save(img)
        inputs["image_path"] = "inputs/product_image_p.jpg"
    if with_video:
        (inputs_dir / "video_clip.mp4").write_bytes(b"fake")
        inputs["video_path"] = "inputs/video_clip.mp4"
    run_manager.update_metadata(run_id, {"inputs": inputs})
    return run_id


async def _collect(run_id: str) -> list[dict]:
    return [event async for event in run_pipeline(run_id)]


async def test_pipeline_text_and_image_no_video(tmp_content_dir: Path):
    run_id = _make_run(tmp_content_dir)
    events = await _collect(run_id)
    names = [e["event"] for e in events]
    assert names == [
        "pipeline_started",
        "text_processed",
        "image_processed",
        "video_skipped",
        "ingestion_complete",
        "pipeline_complete",
    ]

    artifact = json.loads((tmp_content_dir / run_id / "processed" / "ingestion.json").read_text())
    assert set(artifact["text"]) == {"product", "audience", "colors"}
    assert "http" not in artifact["text"]["product"]["content"]
    assert artifact["image"]["image_payload"].startswith("data:image/jpeg;base64,")
    assert "video" not in artifact

    meta = run_manager.get_metadata(run_id)
    assert meta["ingestion"]["artifact_path"] == "processed/ingestion.json"
    assert meta["ingestion"]["image_processed"] is True
    assert meta["ingestion"]["video_frame_count"] == 0


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
    events = await _collect(run_id)
    names = [e["event"] for e in events]
    assert "video_failed" in names
    assert "pipeline_complete" in names  # run still completes
    meta = run_manager.get_metadata(run_id)
    assert meta["ingestion"]["video_frame_count"] == 0


async def test_pipeline_halts_when_image_missing(tmp_content_dir: Path):
    run_id = _make_run(tmp_content_dir, with_image=False)
    events = await _collect(run_id)
    names = [e["event"] for e in events]
    assert "pipeline_error" in names
    assert "pipeline_complete" not in names  # halted
    assert "ingestion_complete" not in names
    meta = run_manager.get_metadata(run_id)
    assert meta["status"] == "failed"
