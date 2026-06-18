from pathlib import Path
from fastapi.testclient import TestClient


def _valid_body(image_token: str, **overrides) -> dict:
    body = {
        "generation_name": "Argan Oil Launch",
        "description_product": "Organic argan oil, 30ml amber dropper bottle.",
        "description_audience": "Women aged 28-45, natural skincare.",
        "description_colors": "Soft pastels, warm cream, matte gold.",
        "product_image_token": image_token,
        "video_token": None,
        "model_3d_token": None,
        "reference_image_token": None,
        "steering": {
            "aspect_ratio": "1:1",
            "camera_perspective": "Studio Eye-Level",
            "lighting_preset": "Studio Softlight",
            "negative_prompts": "",
        },
        "pipeline_mode": "ecommerce",
        "ecommerce_image_count": 5,
        "social_research_enabled": False,
        "ab_concept_directions": "",
        "seasonal_theme": None,
        "supervision": {"research": True, "image_gen": True},
    }
    body.update(overrides)
    return body


def test_submit_returns_run_id(client: TestClient, stage_file):
    token = stage_file("product.jpg")
    response = client.post("/api/runs/submit", json=_valid_body(token))
    assert response.status_code == 201
    body = response.json()
    assert "run_id" in body
    assert len(body["run_id"]) == 36


def test_submit_creates_run_directory(client: TestClient, stage_file, tmp_content_dir: Path):
    token = stage_file("product.jpg")
    response = client.post("/api/runs/submit", json=_valid_body(token))
    run_id = response.json()["run_id"]
    assert (tmp_content_dir / run_id / "inputs").is_dir()


def test_submit_moves_product_image_to_inputs(
    client: TestClient, stage_file, tmp_content_dir: Path
):
    token = stage_file("product.jpg")
    response = client.post("/api/runs/submit", json=_valid_body(token))
    run_id = response.json()["run_id"]
    assert (tmp_content_dir / run_id / "inputs" / "product_image_product.jpg").exists()


def test_submit_writes_run_metadata(client: TestClient, stage_file, tmp_content_dir: Path):
    import json

    token = stage_file("product.jpg")
    response = client.post("/api/runs/submit", json=_valid_body(token))
    run_id = response.json()["run_id"]
    meta = json.loads((tmp_content_dir / run_id / "run_metadata.json").read_text())
    assert meta["run_id"] == run_id
    assert meta["status"] == "running"
    assert meta["pipeline_mode"] == "ecommerce"
    assert meta["inputs"]["description_product"] == "Organic argan oil, 30ml amber dropper bottle."
    assert meta["inputs"]["image_path"] == "inputs/product_image_product.jpg"
    assert meta["steering"]["aspect_ratio"] == "1:1"
    assert meta["supervision"]["research"] is True


def test_submit_persists_generation_name(client: TestClient, stage_file, tmp_content_dir: Path):
    import json

    token = stage_file("product.jpg")
    body = _valid_body(token, generation_name="Summer Sneaker Launch")
    response = client.post("/api/runs/submit", json=body)
    run_id = response.json()["run_id"]
    meta = json.loads((tmp_content_dir / run_id / "run_metadata.json").read_text())
    assert meta["generation_name"] == "Summer Sneaker Launch"


def test_submit_rejects_missing_generation_name(client: TestClient, stage_file):
    token = stage_file("product.jpg")
    body = _valid_body(token, generation_name="")
    response = client.post("/api/runs/submit", json=body)
    assert response.status_code == 422


def test_submit_allows_unset_steering(client: TestClient, stage_file, tmp_content_dir: Path):
    import json

    token = stage_file("product.jpg")
    body = _valid_body(token, steering={
        "aspect_ratio": None,
        "camera_perspective": None,
        "lighting_preset": None,
        "negative_prompts": "",
    })
    response = client.post("/api/runs/submit", json=body)
    assert response.status_code == 201
    run_id = response.json()["run_id"]
    meta = json.loads((tmp_content_dir / run_id / "run_metadata.json").read_text())
    assert meta["steering"]["aspect_ratio"] is None
    assert meta["steering"]["camera_perspective"] is None
    assert meta["steering"]["lighting_preset"] is None


def test_submit_rejects_missing_description_field(client: TestClient, stage_file):
    token = stage_file("product.jpg")
    body = _valid_body(token, description_product="")
    response = client.post("/api/runs/submit", json=body)
    assert response.status_code == 422


def test_submit_rejects_invalid_product_image_token(client: TestClient):
    response = client.post("/api/runs/submit", json=_valid_body("nonexistent-token"))
    assert response.status_code == 422
    assert "token" in response.json()["detail"].lower()


def test_submit_rejects_invalid_pipeline_mode(client: TestClient, stage_file):
    token = stage_file("product.jpg")
    response = client.post("/api/runs/submit", json=_valid_body(token, pipeline_mode="invalid"))
    assert response.status_code == 422


def test_submit_rejects_ecommerce_count_out_of_range(client: TestClient, stage_file):
    token = stage_file("product.jpg")
    body = _valid_body(token, pipeline_mode="ecommerce", ecommerce_image_count=3)
    response = client.post("/api/runs/submit", json=body)
    assert response.status_code == 422


def test_submit_rejects_seasonal_mode_without_theme(client: TestClient, stage_file):
    token = stage_file("product.jpg")
    body = _valid_body(token, pipeline_mode="seasonal", seasonal_theme=None)
    response = client.post("/api/runs/submit", json=body)
    assert response.status_code == 422


def test_submit_with_optional_reference_image_token(
    client: TestClient, stage_file, tmp_content_dir: Path
):
    import json

    img_token = stage_file("product.jpg")
    ref_token = stage_file("reference.png")
    body = _valid_body(img_token, reference_image_token=ref_token)
    response = client.post("/api/runs/submit", json=body)
    assert response.status_code == 201
    run_id = response.json()["run_id"]
    assert (tmp_content_dir / run_id / "inputs" / "reference_image_reference.png").exists()
    meta = json.loads((tmp_content_dir / run_id / "run_metadata.json").read_text())
    assert meta["inputs"]["reference_image_path"] == "inputs/reference_image_reference.png"
