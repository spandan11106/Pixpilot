from app.core.run_manager import run_manager


async def test_serve_image_returns_bytes(tmp_content_dir, client):
    rid = run_manager.create_run()
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    (tmp_content_dir / rid / "v1.png").write_bytes(png_bytes)
    resp = client.get(f"/api/runs/{rid}/images/v1.png")
    assert resp.status_code == 200
    assert resp.content == png_bytes
    assert resp.headers["content-type"].startswith("image/png")


async def test_serve_image_not_found_returns_404(tmp_content_dir, client):
    rid = run_manager.create_run()
    resp = client.get(f"/api/runs/{rid}/images/v1.png")
    assert resp.status_code == 404


async def test_serve_image_path_traversal_rejected(tmp_content_dir, client):
    rid = run_manager.create_run()
    resp = client.get(f"/api/runs/{rid}/images/../run_metadata.json")
    assert resp.status_code in (400, 404, 422)


async def test_serve_image_invalid_extension_rejected(tmp_content_dir, client):
    rid = run_manager.create_run()
    resp = client.get(f"/api/runs/{rid}/images/v1.exe")
    assert resp.status_code == 400
