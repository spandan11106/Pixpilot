import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.settings import settings

_DEFAULTS = {
    "supervision_defaults": {
        "research": True,
        "image_gen": True,
        "captions": True,
    },
    "default_steering": {
        "aspect_ratio": "1:1",
        "camera_perspective": "Studio Eye-Level",
        "lighting_preset": "Studio Softlight",
        "negative_prompts": "",
    },
}


def _settings_path() -> Path:
    return settings.content_dir / "workspace_settings.json"


def init_workspace() -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        write_settings({**_DEFAULTS, "updated_at": _now()})


def read_settings() -> dict:
    path = _settings_path()
    if not path.exists():
        return {**_DEFAULTS, "updated_at": _now()}
    return json.loads(path.read_text())


def write_settings(data: dict) -> None:
    data["updated_at"] = _now()
    _settings_path().write_text(json.dumps(data, indent=2))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
