import io

from fastapi.testclient import TestClient


def test_upload_product_image_returns_token(client: TestClient):
    data = io.BytesIO(b"fake image bytes")
    response = client.post(
        "/api/uploads?file_type=product_image",
        files={"file": ("product.jpg", data, "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert "upload_token" in body
    assert len(body["upload_token"]) == 36  # uuid4


def test_upload_stores_file_on_disk(client: TestClient, tmp_content_dir):
    data = io.BytesIO(b"fake image bytes")
    response = client.post(
        "/api/uploads?file_type=product_image",
        files={"file": ("product.jpg", data, "image/jpeg")},
    )
    token = response.json()["upload_token"]
    staged = tmp_content_dir / "uploads" / token / "product.jpg"
    assert staged.exists()


def test_upload_rejects_wrong_extension(client: TestClient):
    data = io.BytesIO(b"fake")
    response = client.post(
        "/api/uploads?file_type=product_image",
        files={"file": ("product.gif", data, "image/gif")},
    )
    assert response.status_code == 422
    assert "gif" in response.json()["detail"].lower()


def test_upload_rejects_oversized_file(client: TestClient):
    # product_image limit is 20MB; send 21MB
    big = io.BytesIO(b"x" * (21 * 1024 * 1024))
    response = client.post(
        "/api/uploads?file_type=product_image",
        files={"file": ("product.jpg", big, "image/jpeg")},
    )
    assert response.status_code == 422
    assert "size" in response.json()["detail"].lower()


def test_upload_video_accepts_mp4(client: TestClient):
    data = io.BytesIO(b"fake video")
    response = client.post(
        "/api/uploads?file_type=video",
        files={"file": ("clip.mp4", data, "video/mp4")},
    )
    assert response.status_code == 200


def test_upload_video_rejects_avi(client: TestClient):
    data = io.BytesIO(b"fake video")
    response = client.post(
        "/api/uploads?file_type=video",
        files={"file": ("clip.avi", data, "video/avi")},
    )
    assert response.status_code == 422


def test_upload_model_accepts_glb(client: TestClient):
    data = io.BytesIO(b"fake glb")
    response = client.post(
        "/api/uploads?file_type=model_3d",
        files={"file": ("scene.glb", data, "model/gltf-binary")},
    )
    assert response.status_code == 200


def test_upload_model_accepts_zip(client: TestClient):
    data = io.BytesIO(b"fake zip")
    response = client.post(
        "/api/uploads?file_type=model_3d",
        files={"file": ("bundle.zip", data, "application/zip")},
    )
    assert response.status_code == 200


def test_upload_model_rejects_stl(client: TestClient):
    data = io.BytesIO(b"fake stl")
    response = client.post(
        "/api/uploads?file_type=model_3d",
        files={"file": ("scene.stl", data, "model/stl")},
    )
    assert response.status_code == 422
    assert "stl" in response.json()["detail"].lower()


def test_upload_invalid_file_type_param(client: TestClient):
    data = io.BytesIO(b"fake")
    response = client.post(
        "/api/uploads?file_type=unknown",
        files={"file": ("x.jpg", data, "image/jpeg")},
    )
    assert response.status_code == 422
