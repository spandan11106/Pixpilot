import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.run_manager import run_manager


def _setup_run(tmp_content_dir: Path) -> str:
    rid = run_manager.create_run()
    run_dir = tmp_content_dir / rid
    (run_dir / "v1.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)
    processed_dir = run_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    ingestion = {"image": {"image_payload": "data:image/jpeg;base64,/9j/abc=="}, "text": {}}
    (processed_dir / "ingestion.json").write_text(json.dumps(ingestion))
    run_manager.update_metadata(rid, {
        "image_iterations": [{
            "iteration": 1, "prompt": "original serum bottle prompt",
            "seed": 42, "output_path": "v1.png", "feedback": None,
        }],
        "agent_states": {
            "product_profile": {"product_name": "Serum X", "product_category": "skincare"},
        },
        "steering": {"aspect_ratio": "1:1", "negative_prompts": ""},
    })
    return rid


async def test_revise_returns_updated_image(tmp_content_dir, client):
    rid = _setup_run(tmp_content_dir)
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20

    with patch("app.api.routes.revise.rewrite_prompt",
               new=AsyncMock(return_value="revised prompt with darker background")), \
         patch("app.api.routes.revise.generate_image",
               new=AsyncMock(return_value={
                   "image_url": "https://fal.media/out2.jpg",
                   "seed": 99, "latency_ms": 3000,
               })), \
         patch("httpx.AsyncClient") as mock_httpx:
        mock_httpx.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock(get=AsyncMock(return_value=MagicMock(content=fake_png)))
        )
        mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)
        resp = client.post(f"/api/runs/{rid}/revise",
                           json={"feedback": "make background darker", "iteration": 1})

    assert resp.status_code == 200
    data = resp.json()
    assert data["iteration"] == 2
    assert data["image_path"] == "v2.png"
    assert data["image_url"] == f"/api/runs/{rid}/images/v2.png"
    assert data["seed"] == 99
    assert "prompt_used" in data

    assert (tmp_content_dir / rid / "v2.png").exists()
    meta = run_manager.get_metadata(rid)
    assert len(meta["image_iterations"]) == 2
    assert meta["image_iterations"][1]["feedback"] == "make background darker"
    assert meta["image_iterations"][1]["iteration"] == 2


async def test_revise_max_iterations_returns_400(tmp_content_dir, client):
    rid = _setup_run(tmp_content_dir)
    resp = client.post(f"/api/runs/{rid}/revise",
                       json={"feedback": "change something", "iteration": 10})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "max_iterations_reached"


async def test_revise_run_not_found_returns_404(tmp_content_dir, client):
    resp = client.post(
        "/api/runs/00000000-0000-4000-8000-000000000000/revise",
        json={"feedback": "test", "iteration": 1},
    )
    assert resp.status_code == 404


async def test_revise_missing_metadata_returns_404(tmp_content_dir, client):
    rid = run_manager.create_run()
    # Delete the metadata file so the directory exists but metadata is missing
    metadata_path = tmp_content_dir / rid / "run_metadata.json"
    metadata_path.unlink()
    resp = client.post(f"/api/runs/{rid}/revise",
                       json={"feedback": "test", "iteration": 1})
    assert resp.status_code == 404


async def test_revise_refinement_failure_returns_500(tmp_content_dir, client):
    rid = _setup_run(tmp_content_dir)
    with patch("app.api.routes.revise.rewrite_prompt",
               new=AsyncMock(side_effect=RuntimeError("Anthropic error"))):
        resp = client.post(f"/api/runs/{rid}/revise",
                           json={"feedback": "change something", "iteration": 1})
    assert resp.status_code == 500


async def test_revise_fal_failure_returns_500(tmp_content_dir, client):
    rid = _setup_run(tmp_content_dir)
    with patch("app.api.routes.revise.rewrite_prompt",
               new=AsyncMock(return_value="revised")), \
         patch("app.api.routes.revise.generate_image",
               new=AsyncMock(side_effect=Exception("fal error"))):
        resp = client.post(f"/api/runs/{rid}/revise",
                           json={"feedback": "change something", "iteration": 1})
    assert resp.status_code == 500
