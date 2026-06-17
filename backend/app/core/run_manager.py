import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.settings import settings

_INITIAL_METADATA = {
    "run_id": None,
    "created_at": None,
    "completed_at": None,
    "status": "running",
    "pipeline_mode": None,
    "seasonal_theme": None,
    "inputs": {},
    "steering": {},
    "supervision": {},
    "agent_states": {
        "product_profile": None,
        "market_report": None,
        "creative_blueprint": None,
    },
    "image_iterations": [],
    "approved_image": None,
    "user_rating": None,
    "user_feedback_text": None,
}


class RunManager:
    def __init__(self, content_dir: Path | None = None) -> None:
        self._root = content_dir or settings.content_dir

    def _run_dir(self, run_id: str) -> Path:
        return self._root / run_id

    def _metadata_path(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "run_metadata.json"

    def create_run(self) -> str:
        run_id = str(uuid.uuid4())
        run_dir = self._run_dir(run_id)
        (run_dir / "inputs").mkdir(parents=True, exist_ok=True)

        metadata = {
            **_INITIAL_METADATA,
            "run_id": run_id,
            "created_at": _now(),
        }
        self._write(run_id, metadata)
        return run_id

    def update_metadata(self, run_id: str, patch: dict) -> None:
        current = self.get_metadata(run_id)
        _deep_merge(current, patch)
        self._write(run_id, current)

    def get_metadata(self, run_id: str) -> dict:
        path = self._metadata_path(run_id)
        if not path.exists():
            raise FileNotFoundError(f"No run found: {run_id}")
        return json.loads(path.read_text())

    def get_content_dir(self) -> Path:
        return self._root

    def _write(self, run_id: str, data: dict) -> None:
        path = self._metadata_path(run_id)
        path.write_text(json.dumps(data, indent=2, default=str))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deep_merge(base: dict, patch: dict) -> None:
    for key, value in patch.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


run_manager = RunManager()
