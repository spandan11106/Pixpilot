import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.settings import settings
from app.main import app


@pytest.fixture()
def tmp_content_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "content_dir", tmp_path)
    # also patch run_manager and uploads module after import
    from app.core import run_manager as rm_module
    monkeypatch.setattr(rm_module.run_manager, "_root", tmp_path)
    return tmp_path


@pytest.fixture()
def client(tmp_content_dir: Path) -> TestClient:
    return TestClient(app)


@pytest.fixture()
def stage_file(tmp_content_dir: Path):
    """Helper: pre-stage a file and return its upload_token."""
    import uuid

    def _stage(filename: str, content: bytes = b"fake") -> str:
        token = str(uuid.uuid4())
        dest = tmp_content_dir / "uploads" / token
        dest.mkdir(parents=True)
        (dest / filename).write_bytes(content)
        return token

    return _stage
