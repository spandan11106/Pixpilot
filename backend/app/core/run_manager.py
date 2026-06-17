import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

        metadata = {**_INITIAL_METADATA, "run_id": run_id, "created_at": _now()}
        self._write(run_id, metadata)
        return run_id

    def create_run_from_submission(
        self,
        payload: dict[str, Any],
        file_map: dict[str, Path],
    ) -> str:
        """
        Create a run, move staged files into inputs/, write full run_metadata.json.

        payload: the validated SubmitPayload dict (model_dump())
        file_map: mapping of field name → absolute Path of staged file
                  e.g. {"product_image": Path("/content/uploads/<token>/product.jpg")}
        """
        run_id = str(uuid.uuid4())
        inputs_dir = self._run_dir(run_id) / "inputs"
        inputs_dir.mkdir(parents=True, exist_ok=True)

        # Move staged files into inputs/
        path_map: dict[str, str | None] = {}
        for field, src in file_map.items():
            dest = inputs_dir / src.name
            shutil.move(str(src), dest)
            path_map[field] = f"inputs/{src.name}"

        inputs_meta = {
            "description_product": payload["description_product"],
            "description_audience": payload["description_audience"],
            "description_colors": payload["description_colors"],
            "image_path": path_map.get("product_image"),
            "video_path": path_map.get("video"),
            "model_3d_path": path_map.get("model_3d"),
            "reference_image_path": path_map.get("reference_image"),
            "logo_path": path_map.get("logo"),
            "logo_placement": payload.get("logo_placement"),
        }

        metadata = {
            **_INITIAL_METADATA,
            "run_id": run_id,
            "created_at": _now(),
            "pipeline_mode": payload["pipeline_mode"],
            "seasonal_theme": payload.get("seasonal_theme"),
            "inputs": inputs_meta,
            "steering": payload["steering"],
            "supervision": payload["supervision"],
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
