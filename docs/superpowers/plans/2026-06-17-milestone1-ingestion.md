# Milestone 1 — Submission Form & Ingestion Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Next.js submission form and FastAPI ingestion endpoints that accept, validate, and store all pipeline inputs, returning a `run_id` to wire into the existing SSE pipeline view.

**Architecture:** Files upload immediately on selection via `POST /api/uploads` (returning an `upload_token`). On submit, `POST /api/runs/submit` receives only text fields + tokens, resolves tokens to staged files, moves them into the run directory, writes `run_metadata.json`, and returns `run_id`. The frontend is a functional accordion form — no visual polish.

**Tech Stack:** FastAPI (Python 3.11+), Pydantic v2, pytest + pytest-asyncio + httpx (TestClient), Next.js 16 (App Router), React 19, shadcn/ui, Tailwind CSS v4.

## Global Constraints

- Python ≥ 3.11; use `Path` not `os.path`
- Pydantic v2 model syntax (`model_config`, `model_validator`, not v1 decorators)
- `asyncio_mode = "auto"` is set in pyproject.toml — no `@pytest.mark.asyncio` needed
- All backend tests go under `backend/tests/`; run from repo root as `pytest backend/tests/`
- `python-multipart`, `aiofiles`, `httpx` already in dependencies — do not add them again
- Frontend: no new npm packages — all shadcn components are added via `npx shadcn add <name>` from inside `frontend/`
- Frontend tests: none required for this milestone — functional correctness is verified via the backend tests + manual smoke test
- Staged upload files live at `content/uploads/<upload_token>/<filename>` (inside `settings.content_dir`)
- Run input files live at `content/<run_id>/inputs/<filename>`
- `run_manager` singleton is imported from `app.core.run_manager`
- `settings` singleton is imported from `app.core.settings`
- Line length: 100 chars (ruff enforced)

---

## File Map

**Create:**
- `backend/tests/__init__.py` — empty, makes tests a package
- `backend/tests/conftest.py` — shared pytest fixtures (TestClient, tmp content_dir)
- `backend/tests/test_uploads.py` — tests for `POST /api/uploads`
- `backend/tests/test_runs_submit.py` — tests for `POST /api/runs/submit`
- `backend/app/api/routes/uploads.py` — upload endpoint
- `frontend/lib/upload.ts` — `uploadFile(file, fileType)` → `Promise<string>` (returns upload_token)
- `frontend/lib/submit.ts` — `submitRun(payload)` → `Promise<string>` (returns run_id)

**Modify:**
- `backend/app/api/routes/runs.py` — add `POST /api/runs/submit` route
- `backend/app/core/run_manager.py` — add `create_run_with_metadata(run_id, payload, file_map)` method
- `backend/app/main.py` — register uploads router
- `frontend/app/page.tsx` — replace stub with accordion form

---

## Task 1: Test infrastructure and conftest

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

**Interfaces:**
- Produces: `client` fixture (FastAPI TestClient), `tmp_content_dir` fixture (tmp_path-based Path), `stage_file` fixture (helper to pre-stage a file token)

- [ ] **Step 1: Create the empty package file**

```python
# backend/tests/__init__.py
# (empty)
```

- [ ] **Step 2: Write conftest.py**

```python
# backend/tests/conftest.py
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
```

- [ ] **Step 3: Verify conftest loads without error**

Run from repo root:
```bash
cd /path/to/repo && pytest backend/tests/ --collect-only
```
Expected: `no tests ran` with 0 errors.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/__init__.py backend/tests/conftest.py
git commit -m "test: add pytest conftest with TestClient and tmp_content_dir fixtures"
```

---

## Task 2: Upload endpoint — backend

**Files:**
- Create: `backend/tests/test_uploads.py`
- Create: `backend/app/api/routes/uploads.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `POST /api/uploads?file_type=<type>` → `{"upload_token": "<uuid>"}`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_uploads.py
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
    from pathlib import Path

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


def test_upload_invalid_file_type_param(client: TestClient):
    data = io.BytesIO(b"fake")
    response = client.post(
        "/api/uploads?file_type=unknown",
        files={"file": ("x.jpg", data, "image/jpeg")},
    )
    assert response.status_code == 422
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest backend/tests/test_uploads.py -v
```
Expected: all tests FAIL (404 or import error — route doesn't exist yet).

- [ ] **Step 3: Write the uploads route**

```python
# backend/app/api/routes/uploads.py
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.core.settings import settings

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

FileType = Literal["product_image", "reference_image", "logo", "video", "model_3d"]

_RULES: dict[str, dict] = {
    "product_image":   {"exts": {"jpg", "jpeg", "png", "webp"}, "max_mb": 20},
    "reference_image": {"exts": {"jpg", "jpeg", "png", "webp"}, "max_mb": 20},
    "logo":            {"exts": {"svg", "png", "jpeg", "jpg"}, "max_mb": 10},
    "video":           {"exts": {"mp4", "mov", "webm"}, "max_mb": 100},
    "model_3d":        {"exts": {"gltf", "obj", "usdz"}, "max_mb": 50},
}


class UploadResponse(BaseModel):
    upload_token: str


@router.post("", response_model=UploadResponse)
async def upload_file(
    file_type: FileType = Query(...),
    file: UploadFile = File(...),
) -> UploadResponse:
    rule = _RULES[file_type]
    ext = Path(file.filename or "").suffix.lstrip(".").lower()
    if ext not in rule["exts"]:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid extension '.{ext}' for {file_type}. "
                   f"Accepted: {sorted(rule['exts'])}",
        )

    content = await file.read()
    max_bytes = rule["max_mb"] * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=422,
            detail=f"File size {len(content)} bytes exceeds {rule['max_mb']}MB size limit.",
        )

    token = str(uuid.uuid4())
    dest_dir: Path = settings.content_dir / "uploads" / token
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / (file.filename or "upload")).write_bytes(content)

    return UploadResponse(upload_token=token)
```

- [ ] **Step 4: Register the router in main.py**

In `backend/app/main.py`, add:
```python
from app.api.routes import runs, sse, uploads   # add uploads

# in the router registration block, add:
app.include_router(uploads.router)
```

Full updated `main.py`:
```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import runs, sse, uploads
from app.core.settings import settings
from app.core.workspace import init_workspace


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_workspace()
    yield


app = FastAPI(
    title="Pixpilot API",
    description="AI-assisted product image & copy generation pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs.router)
app.include_router(sse.router)
app.include_router(uploads.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
pytest backend/tests/test_uploads.py -v
```
Expected: all 7 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/uploads.py backend/app/main.py backend/tests/test_uploads.py
git commit -m "feat: add POST /api/uploads endpoint with file type and size validation"
```

---

## Task 3: Extend RunManager and add submit endpoint — backend

**Files:**
- Create: `backend/tests/test_runs_submit.py`
- Modify: `backend/app/core/run_manager.py`
- Modify: `backend/app/api/routes/runs.py`

**Interfaces:**
- Consumes: `stage_file` fixture from conftest; `POST /api/uploads` token from Task 2
- Produces: `POST /api/runs/submit` → `{"run_id": "<uuid>"}` + files at `content/<run_id>/inputs/` + fully populated `run_metadata.json`
- Produces: `run_manager.create_run_from_submission(payload: SubmitPayload, file_map: dict[str, Path]) -> str`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_runs_submit.py
from pathlib import Path
from fastapi.testclient import TestClient


def _valid_body(image_token: str, **overrides) -> dict:
    body = {
        "description_product": "Organic argan oil, 30ml amber dropper bottle.",
        "description_audience": "Women aged 28-45, natural skincare.",
        "description_colors": "Soft pastels, warm cream, matte gold.",
        "product_image_token": image_token,
        "video_token": None,
        "model_3d_token": None,
        "reference_image_token": None,
        "logo_token": None,
        "logo_placement": "bottom-left",
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
    assert (tmp_content_dir / run_id / "inputs" / "product.jpg").exists()


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
    assert meta["inputs"]["image_path"] == "inputs/product.jpg"
    assert meta["steering"]["aspect_ratio"] == "1:1"
    assert meta["supervision"]["research"] is True


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


def test_submit_with_optional_logo_token(
    client: TestClient, stage_file, tmp_content_dir: Path
):
    import json

    img_token = stage_file("product.jpg")
    logo_token = stage_file("logo.png")
    body = _valid_body(img_token, logo_token=logo_token, logo_placement="top-right")
    response = client.post("/api/runs/submit", json=body)
    assert response.status_code == 201
    run_id = response.json()["run_id"]
    assert (tmp_content_dir / run_id / "inputs" / "logo.png").exists()
    meta = json.loads((tmp_content_dir / run_id / "run_metadata.json").read_text())
    assert meta["inputs"]["logo_path"] == "inputs/logo.png"
    assert meta["inputs"]["logo_placement"] == "top-right"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest backend/tests/test_runs_submit.py -v
```
Expected: all tests FAIL (404 — route doesn't exist yet).

- [ ] **Step 3: Add `create_run_from_submission` to RunManager**

Replace the contents of `backend/app/core/run_manager.py` with:

```python
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
```

- [ ] **Step 4: Add the submit route to runs.py**

Replace `backend/app/api/routes/runs.py` with:

```python
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.core.run_manager import run_manager
from app.core.settings import settings

router = APIRouter(prefix="/api/runs", tags=["runs"])

PipelineMode = Literal["summarize", "ecommerce", "social", "ab", "seasonal"]

SeasonalTheme = Literal[
    "Christmas", "Halloween", "Summer", "Spring", "Diwali",
    "Black Friday", "Valentine's Day", "Eid", "Hanukkah", "New Year",
]

LogoPlacement = Literal[
    "top-left", "top-right", "bottom-left", "bottom-right", "center-watermark"
]


class SteeringParams(BaseModel):
    aspect_ratio: Literal["1:1", "9:16", "16:9", "4:5"] = "1:1"
    camera_perspective: Literal[
        "Studio Eye-Level", "Flat Lay (Top-Down)", "Close-Up Macro",
        "Dynamic 3/4 View", "Hero Shot (Low Angle)",
    ] = "Studio Eye-Level"
    lighting_preset: Literal[
        "Studio Softlight", "Natural Sunshine", "Golden Hour Warmth",
        "Moody / Chiaroscuro", "Neon / Cyberpunk", "Minimalist Pastel",
    ] = "Studio Softlight"
    negative_prompts: str = ""


class SupervisionSettings(BaseModel):
    research: bool = True
    image_gen: bool = True


class SubmitPayload(BaseModel):
    description_product: Annotated[str, Field(min_length=1)]
    description_audience: Annotated[str, Field(min_length=1)]
    description_colors: Annotated[str, Field(min_length=1)]

    product_image_token: str
    video_token: str | None = None
    model_3d_token: str | None = None
    reference_image_token: str | None = None
    logo_token: str | None = None
    logo_placement: LogoPlacement = "bottom-left"

    steering: SteeringParams = SteeringParams()
    pipeline_mode: PipelineMode = "ecommerce"
    ecommerce_image_count: int = 5
    social_research_enabled: bool = False
    ab_concept_directions: str = ""
    seasonal_theme: SeasonalTheme | None = None
    supervision: SupervisionSettings = SupervisionSettings()

    @model_validator(mode="after")
    def validate_mode_fields(self) -> "SubmitPayload":
        if self.pipeline_mode == "ecommerce":
            if not (5 <= self.ecommerce_image_count <= 12):
                raise ValueError("ecommerce_image_count must be between 5 and 12")
        if self.pipeline_mode == "seasonal" and self.seasonal_theme is None:
            raise ValueError("seasonal_theme is required when pipeline_mode is 'seasonal'")
        return self


class CreateRunResponse(BaseModel):
    run_id: str


def _resolve_token(token: str | None, label: str) -> Path | None:
    if token is None:
        return None
    token_dir = settings.content_dir / "uploads" / token
    if not token_dir.exists():
        raise HTTPException(
            status_code=422,
            detail=f"Invalid token for {label}: '{token}' not found.",
        )
    files = list(token_dir.iterdir())
    if not files:
        raise HTTPException(
            status_code=422,
            detail=f"Token directory for {label} is empty.",
        )
    return files[0]


@router.post("", response_model=CreateRunResponse, status_code=201)
async def create_run() -> CreateRunResponse:
    run_id = run_manager.create_run()
    return CreateRunResponse(run_id=run_id)


@router.get("/{run_id}/metadata")
async def get_run_metadata(run_id: str) -> dict:
    return run_manager.get_metadata(run_id)


@router.post("/submit", response_model=CreateRunResponse, status_code=201)
async def submit_run(payload: SubmitPayload) -> CreateRunResponse:
    product_image_path = _resolve_token(payload.product_image_token, "product_image")
    if product_image_path is None:
        raise HTTPException(status_code=422, detail="product_image_token is required.")

    file_map: dict[str, Path] = {"product_image": product_image_path}
    optional_tokens = {
        "video": payload.video_token,
        "model_3d": payload.model_3d_token,
        "reference_image": payload.reference_image_token,
        "logo": payload.logo_token,
    }
    for field, token in optional_tokens.items():
        path = _resolve_token(token, field)
        if path is not None:
            file_map[field] = path

    run_id = run_manager.create_run_from_submission(
        payload=payload.model_dump(),
        file_map=file_map,
    )
    return CreateRunResponse(run_id=run_id)
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
pytest backend/tests/test_runs_submit.py -v
```
Expected: all 10 tests PASS.

- [ ] **Step 6: Run full test suite to confirm no regressions**

```bash
pytest backend/tests/ -v
```
Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/run_manager.py backend/app/api/routes/runs.py backend/tests/test_runs_submit.py
git commit -m "feat: add POST /api/runs/submit with validation, file resolution, and metadata write"
```

---

## Task 4: Frontend — shadcn components and helper libs

**Files:**
- Add shadcn components via CLI (run from `frontend/`)
- Create: `frontend/lib/upload.ts`
- Create: `frontend/lib/submit.ts`

**Interfaces:**
- Produces: `uploadFile(file: File, fileType: string): Promise<string>` — returns upload_token
- Produces: `submitRun(payload: SubmitPayload): Promise<string>` — returns run_id

- [ ] **Step 1: Install missing shadcn components**

Run from inside `frontend/`:
```bash
cd frontend
npx shadcn add accordion label textarea select switch input
```
Accept all prompts. This writes files to `frontend/components/ui/`.

- [ ] **Step 2: Write upload.ts**

```typescript
// frontend/lib/upload.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function uploadFile(file: File, fileType: string): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/api/uploads?file_type=${fileType}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Upload failed: ${res.status}`);
  }
  const { upload_token } = await res.json();
  return upload_token as string;
}
```

- [ ] **Step 3: Write submit.ts**

```typescript
// frontend/lib/submit.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface SteeringParams {
  aspect_ratio: string;
  camera_perspective: string;
  lighting_preset: string;
  negative_prompts: string;
}

export interface SupervisionSettings {
  research: boolean;
  image_gen: boolean;
}

export interface SubmitPayload {
  description_product: string;
  description_audience: string;
  description_colors: string;
  product_image_token: string;
  video_token: string | null;
  model_3d_token: string | null;
  reference_image_token: string | null;
  logo_token: string | null;
  logo_placement: string;
  steering: SteeringParams;
  pipeline_mode: string;
  ecommerce_image_count: number;
  social_research_enabled: boolean;
  ab_concept_directions: string;
  seasonal_theme: string | null;
  supervision: SupervisionSettings;
}

export async function submitRun(payload: SubmitPayload): Promise<string> {
  const res = await fetch(`${API_URL}/api/runs/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Submit failed: ${res.status}`);
  }
  const { run_id } = await res.json();
  return run_id as string;
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/components/ui/ frontend/lib/upload.ts frontend/lib/submit.ts
git commit -m "feat: add shadcn accordion/label/textarea/select/switch/input and upload/submit lib helpers"
```

---

## Task 5: Frontend — submission form

**Files:**
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: `uploadFile` from `frontend/lib/upload.ts`
- Consumes: `submitRun`, `SubmitPayload` from `frontend/lib/submit.ts`
- Consumes: `useSSE` from `frontend/lib/sse.ts` (unchanged)

- [ ] **Step 1: Replace page.tsx with the accordion form**

```tsx
// frontend/app/page.tsx
"use client";

import { useState, useRef } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { useSSE } from "@/lib/sse";
import { uploadFile } from "@/lib/upload";
import { submitRun, SubmitPayload } from "@/lib/submit";

type UploadState = { token: string | null; status: "idle" | "uploading" | "ready" | "error"; error?: string };

function useFileUpload(fileType: string) {
  const [state, setState] = useState<UploadState>({ token: null, status: "idle" });

  async function handleFile(file: File) {
    setState({ token: null, status: "uploading" });
    try {
      const token = await uploadFile(file, fileType);
      setState({ token, status: "ready" });
    } catch (e) {
      setState({ token: null, status: "error", error: e instanceof Error ? e.message : "Upload failed" });
    }
  }

  function clear() {
    setState({ token: null, status: "idle" });
  }

  return { state, handleFile, clear };
}

function FileField({ label, fileType, accept, onToken }: {
  label: string; fileType: string; accept: string; onToken?: (token: string | null) => void;
}) {
  const { state, handleFile, clear } = useFileUpload(fileType);

  function onChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    handleFile(file).then(() => onToken?.(state.token));
  }

  // notify parent when token changes
  const prev = useRef<string | null>(null);
  if (prev.current !== state.token) {
    prev.current = state.token;
    onToken?.(state.token);
  }

  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      <Input type="file" accept={accept} onChange={onChange} />
      {state.status === "uploading" && <p className="text-xs text-muted-foreground">uploading…</p>}
      {state.status === "ready" && <p className="text-xs text-green-600">ready</p>}
      {state.status === "error" && <p className="text-xs text-destructive">{state.error}</p>}
    </div>
  );
}

export default function Home() {
  const [runId, setRunId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const { messages, connected } = useSSE(runId);

  // Required
  const [productImageToken, setProductImageToken] = useState<string | null>(null);
  const [descProduct, setDescProduct] = useState("");
  const [descAudience, setDescAudience] = useState("");
  const [descColors, setDescColors] = useState("");

  // Optional media tokens
  const [videoToken, setVideoToken] = useState<string | null>(null);
  const [model3dToken, setModel3dToken] = useState<string | null>(null);
  const [referenceToken, setReferenceToken] = useState<string | null>(null);
  const [logoToken, setLogoToken] = useState<string | null>(null);
  const [logoPlacement, setLogoPlacement] = useState("bottom-left");

  // Steering
  const [aspectRatio, setAspectRatio] = useState("1:1");
  const [cameraPerspective, setCameraPerspective] = useState("Studio Eye-Level");
  const [lightingPreset, setLightingPreset] = useState("Studio Softlight");
  const [negativePrompts, setNegativePrompts] = useState("");

  // Mode
  const [pipelineMode, setPipelineMode] = useState("ecommerce");
  const [ecommerceCount, setEcommerceCount] = useState(5);
  const [socialResearch, setSocialResearch] = useState(false);
  const [abDirections, setAbDirections] = useState("");
  const [seasonalTheme, setSeasonalTheme] = useState<string | null>(null);

  // Supervision
  const [supervisionResearch, setSupervisionResearch] = useState(true);
  const [supervisionImageGen, setSupervisionImageGen] = useState(true);

  const canSubmit = !!productImageToken && descProduct.trim() && descAudience.trim() && descColors.trim();

  async function handleSubmit() {
    if (!productImageToken) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const payload: SubmitPayload = {
        description_product: descProduct.trim(),
        description_audience: descAudience.trim(),
        description_colors: descColors.trim(),
        product_image_token: productImageToken,
        video_token: videoToken,
        model_3d_token: model3dToken,
        reference_image_token: referenceToken,
        logo_token: logoToken,
        logo_placement: logoPlacement,
        steering: {
          aspect_ratio: aspectRatio,
          camera_perspective: cameraPerspective,
          lighting_preset: lightingPreset,
          negative_prompts: negativePrompts,
        },
        pipeline_mode: pipelineMode,
        ecommerce_image_count: ecommerceCount,
        social_research_enabled: socialResearch,
        ab_concept_directions: abDirections,
        seasonal_theme: pipelineMode === "seasonal" ? seasonalTheme : null,
        supervision: { research: supervisionResearch, image_gen: supervisionImageGen },
      };
      const id = await submitRun(payload);
      setRunId(id);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-background p-8">
      <div className="mx-auto max-w-3xl space-y-8">
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight">Pixpilot</h1>
          <p className="text-muted-foreground text-lg">AI-assisted product image generation pipeline</p>
        </div>

        <Separator />

        {!runId && (
          <Card>
            <CardHeader><CardTitle>New Run</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <Accordion type="multiple" defaultValue={["required"]}>

                {/* Section 1 — Required */}
                <AccordionItem value="required">
                  <AccordionTrigger>Required Inputs</AccordionTrigger>
                  <AccordionContent className="space-y-4 pt-2">
                    <FileField
                      label="Product Image (jpg/png/webp)"
                      fileType="product_image"
                      accept=".jpg,.jpeg,.png,.webp"
                      onToken={setProductImageToken}
                    />
                    <div className="space-y-1">
                      <Label>Product Info</Label>
                      <Textarea
                        placeholder="Key features, name, USPs…"
                        value={descProduct}
                        onChange={e => setDescProduct(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label>Target Audience</Label>
                      <Textarea
                        placeholder="Who this product is for…"
                        value={descAudience}
                        onChange={e => setDescAudience(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label>Desired Colors</Label>
                      <Textarea
                        placeholder="Color palette preferences…"
                        value={descColors}
                        onChange={e => setDescColors(e.target.value)}
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>

                {/* Section 2 — Optional Media */}
                <AccordionItem value="media">
                  <AccordionTrigger>Optional Media</AccordionTrigger>
                  <AccordionContent className="space-y-4 pt-2">
                    <FileField label="Product Video (mp4/mov/webm, max 100MB)" fileType="video" accept=".mp4,.mov,.webm" onToken={setVideoToken} />
                    <FileField label="3D Model (gltf/obj/usdz, max 50MB)" fileType="model_3d" accept=".gltf,.obj,.usdz" onToken={setModel3dToken} />
                    <FileField label="Reference Image (jpg/png/webp)" fileType="reference_image" accept=".jpg,.jpeg,.png,.webp" onToken={setReferenceToken} />
                    <FileField label="Company Logo (svg/png/jpeg)" fileType="logo" accept=".svg,.png,.jpg,.jpeg" onToken={setLogoToken} />
                    {logoToken && (
                      <div className="space-y-1">
                        <Label>Logo Placement</Label>
                        <Select value={logoPlacement} onValueChange={setLogoPlacement}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="top-left">Top Left</SelectItem>
                            <SelectItem value="top-right">Top Right</SelectItem>
                            <SelectItem value="bottom-left">Bottom Left (default)</SelectItem>
                            <SelectItem value="bottom-right">Bottom Right</SelectItem>
                            <SelectItem value="center-watermark">Center Watermark</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                  </AccordionContent>
                </AccordionItem>

                {/* Section 3 — Visual Steering */}
                <AccordionItem value="steering">
                  <AccordionTrigger>Visual Steering</AccordionTrigger>
                  <AccordionContent className="space-y-4 pt-2">
                    <div className="space-y-1">
                      <Label>Aspect Ratio</Label>
                      <Select value={aspectRatio} onValueChange={setAspectRatio}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="1:1">1:1 Square</SelectItem>
                          <SelectItem value="9:16">9:16 Vertical</SelectItem>
                          <SelectItem value="16:9">16:9 Landscape</SelectItem>
                          <SelectItem value="4:5">4:5 Portrait</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label>Camera Perspective</Label>
                      <Select value={cameraPerspective} onValueChange={setCameraPerspective}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Studio Eye-Level">Studio Eye-Level</SelectItem>
                          <SelectItem value="Flat Lay (Top-Down)">Flat Lay (Top-Down)</SelectItem>
                          <SelectItem value="Close-Up Macro">Close-Up Macro</SelectItem>
                          <SelectItem value="Dynamic 3/4 View">Dynamic 3/4 View</SelectItem>
                          <SelectItem value="Hero Shot (Low Angle)">Hero Shot (Low Angle)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label>Lighting / Vibe Preset</Label>
                      <Select value={lightingPreset} onValueChange={setLightingPreset}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Studio Softlight">Studio Softlight</SelectItem>
                          <SelectItem value="Natural Sunshine">Natural Sunshine</SelectItem>
                          <SelectItem value="Golden Hour Warmth">Golden Hour Warmth</SelectItem>
                          <SelectItem value="Moody / Chiaroscuro">Moody / Chiaroscuro</SelectItem>
                          <SelectItem value="Neon / Cyberpunk">Neon / Cyberpunk</SelectItem>
                          <SelectItem value="Minimalist Pastel">Minimalist Pastel</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label>Negative Prompts</Label>
                      <Textarea
                        placeholder="Elements to exclude…"
                        value={negativePrompts}
                        onChange={e => setNegativePrompts(e.target.value)}
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>

                {/* Section 4 — Pipeline Mode */}
                <AccordionItem value="mode">
                  <AccordionTrigger>Pipeline Mode</AccordionTrigger>
                  <AccordionContent className="space-y-4 pt-2">
                    <div className="space-y-1">
                      <Label>Mode</Label>
                      <Select value={pipelineMode} onValueChange={setPipelineMode}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="ecommerce">E-Commerce Batch</SelectItem>
                          <SelectItem value="social">Social Media Marketing</SelectItem>
                          <SelectItem value="ab">A/B Concept Exploration</SelectItem>
                          <SelectItem value="seasonal">Seasonal / Holiday Campaign</SelectItem>
                          <SelectItem value="summarize">Summarization & Research Opt-In</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    {pipelineMode === "ecommerce" && (
                      <div className="space-y-1">
                        <Label>Number of Images (5–12)</Label>
                        <Input
                          type="number"
                          min={5}
                          max={12}
                          value={ecommerceCount}
                          onChange={e => setEcommerceCount(Number(e.target.value))}
                        />
                      </div>
                    )}
                    {pipelineMode === "social" && (
                      <div className="flex items-center gap-2">
                        <Switch checked={socialResearch} onCheckedChange={setSocialResearch} />
                        <Label>Enable Market Research</Label>
                      </div>
                    )}
                    {pipelineMode === "ab" && (
                      <div className="space-y-1">
                        <Label>Concept Directions (optional)</Label>
                        <Textarea
                          placeholder="Leave blank for agent to choose…"
                          value={abDirections}
                          onChange={e => setAbDirections(e.target.value)}
                        />
                      </div>
                    )}
                    {pipelineMode === "seasonal" && (
                      <div className="space-y-1">
                        <Label>Seasonal Theme</Label>
                        <Select value={seasonalTheme ?? ""} onValueChange={v => setSeasonalTheme(v || null)}>
                          <SelectTrigger><SelectValue placeholder="Select theme…" /></SelectTrigger>
                          <SelectContent>
                            {["Christmas","Halloween","Summer","Spring","Diwali","Black Friday","Valentine's Day","Eid","Hanukkah","New Year"].map(t => (
                              <SelectItem key={t} value={t}>{t}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                  </AccordionContent>
                </AccordionItem>

                {/* Section 5 — Supervision */}
                <AccordionItem value="supervision">
                  <AccordionTrigger>Supervision</AccordionTrigger>
                  <AccordionContent className="space-y-3 pt-2">
                    <div className="flex items-center gap-2">
                      <Switch checked={supervisionResearch} onCheckedChange={setSupervisionResearch} />
                      <Label>Research supervision</Label>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch checked={supervisionImageGen} onCheckedChange={setSupervisionImageGen} />
                      <Label>Image generation supervision</Label>
                    </div>
                    <p className="text-xs text-muted-foreground">Final Review Deck is always shown.</p>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>

              <Button onClick={handleSubmit} disabled={!canSubmit || submitting}>
                {submitting ? "Submitting…" : "Run Pipeline"}
              </Button>
              {submitError && <p className="text-destructive text-sm">{submitError}</p>}
            </CardContent>
          </Card>
        )}

        {runId && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Pipeline Events</CardTitle>
                <Badge variant={connected ? "default" : "secondary"}>
                  {connected ? "Connected" : "Done"}
                </Badge>
              </div>
              <p className="font-mono text-xs text-muted-foreground">{runId}</p>
            </CardHeader>
            <CardContent>
              <div className="bg-muted rounded-md p-4 space-y-2 max-h-80 overflow-y-auto font-mono text-sm">
                {messages.length === 0 && <p className="text-muted-foreground">Waiting for events…</p>}
                {messages.map((msg, i) => (
                  <div key={i} className="flex gap-3">
                    <span className="text-primary font-semibold">[{msg.event}]</span>
                    <span className="text-muted-foreground break-all">{JSON.stringify(msg.data)}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat: replace stub with accordion submission form wired to upload and submit endpoints"
```

---

## Task 6: Smoke test end-to-end

- [ ] **Step 1: Start the stack**

```bash
docker compose up --build
```
Wait for both `backend` and `frontend` containers to report ready.

- [ ] **Step 2: Open the dashboard**

Open `http://localhost:3000` in a browser. Verify the accordion form loads.

- [ ] **Step 3: Upload a product image**

In the Required Inputs section, select any `.jpg` file. Verify the label changes to "ready".

- [ ] **Step 4: Fill in the three description fields**

Verify the "Run Pipeline" button becomes enabled.

- [ ] **Step 5: Click Run Pipeline**

Verify the form is replaced by the Pipeline Events card, with the `run_id` shown and "Waiting for events…" displayed.

- [ ] **Step 6: Verify run directory on disk**

Inside the backend container or the mapped volume:
```bash
ls content/<run_id>/inputs/
cat content/<run_id>/run_metadata.json
```
Expected: product image file present; `run_metadata.json` has correct `pipeline_mode`, `inputs`, `steering`, `supervision`, and `status: "running"`.

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Accordion form with 5 sections | Task 5 |
| Required: product image + 3 description fields | Tasks 2, 5 |
| Optional: video, 3D, reference image, logo + corner | Tasks 2, 3, 5 |
| Visual steering dropdowns | Tasks 3, 5 |
| Mode selector with conditional fields | Tasks 3, 5 |
| Supervision toggles | Tasks 3, 5 |
| Submit disabled until required fields filled | Task 5 |
| `POST /api/uploads` with file type + size validation | Task 2 |
| `POST /api/runs/submit` with field + token validation | Task 3 |
| Files moved to `content/<run_id>/inputs/` | Task 3 |
| `run_metadata.json` written with full payload | Task 3 |
| Per-file upload progress label | Task 5 (FileField component) |
| Transitions to SSE view on success | Task 5 |

All spec requirements covered. No gaps.
