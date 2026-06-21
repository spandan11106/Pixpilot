# Image Designer Agent (Milestone 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add FLUX Dev image-to-image generation via fal.ai to the pipeline, plus a revision loop where users request changes in natural language (up to 10 iterations).

**Architecture:** A new `image_designer.py` agent module provides a prompt builder, fal.ai async client, and a Refinement Agent (Claude Sonnet). Two new LangGraph nodes (`image_designer_start`, `image_designer`) emit SSE events before and after the fal.ai call. A new `revise.py` route handles revision POST requests and image serving GET requests. `ImageWorkspace.tsx` renders inline in the SSE event log after generation completes.

**Tech Stack:** fal-client (fal.ai Python SDK), httpx (image download), anthropic SDK (Refinement Agent), FastAPI, LangGraph, React/TypeScript

## Global Constraints

- Python ≥ 3.11; ruff lint (`ruff check app tests`); pytest asyncio auto-mode
- fal.ai model: `fal-ai/flux/dev/image-to-image` (overridable via `FAL_IMAGE_MODEL` env var)
- All fal.ai calls mocked in tests — no live network calls
- Max revision iterations: 10 (enforced server-side in `POST /api/runs/{run_id}/revise`)
- Generated images saved to `content/<run_id>/v{n}.png` (1-indexed)
- `image_iterations` array in `run_metadata.json` is the source of truth for revision history
- Frontend uses existing dashboard CSS classes; new classes added to `dashboard.css`

---

### Task 1: Add `fal-client` dependency and `fal_image_model` setting

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/core/settings.py`

**Interfaces:**
- Produces: `settings.fal_image_model: str` used by Tasks 3, 5, 6
- Produces: `fal_client` importable in backend Python

- [ ] **Step 1: Add `fal-client` to `pyproject.toml`**

In `backend/pyproject.toml`, add to the `dependencies` list:

```toml
[project]
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "langgraph>=0.2.0",
    "langchain-core>=0.3.0",
    "httpx>=0.27.0",
    "python-multipart>=0.0.9",
    "aiofiles>=24.1.0",
    "Pillow>=10.3.0",
    "openai>=1.0.0",
    "anthropic>=0.25.0",
    "google-genai>=2.0.0",
    "python-dotenv>=1.0.0",
    "fal-client>=0.15.0",
]
```

- [ ] **Step 2: Add `fal_image_model` to `settings.py`**

In `backend/app/core/settings.py`, add an image generation section after `prompt_model`:

```python
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    fal_api_key: str = ""
    serpapi_api_key: str = ""

    # Vision agent
    vision_models: str = "openai,anthropic,google"
    openai_vision_model: str = "gpt-4o"
    anthropic_vision_model: str = "claude-3-5-sonnet-20241022"
    google_vision_model: str = "gemini-2.0-flash"

    # Summary agent
    summary_model: str = "claude-haiku-4-5-20251001"
    prompt_model: str = "claude-sonnet-4-6"

    # Image generation
    fal_image_model: str = "fal-ai/flux/dev/image-to-image"

    # Sidecar URLs
    ffmpeg_sidecar_url: str = "http://ffmpeg:8001"
    renderer_sidecar_url: str = "http://renderer:8002"

    # Storage
    content_dir: Path = Path("/app/content")

    # Server
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
```

- [ ] **Step 3: Install the new dependency**

```bash
cd backend && pip install -e ".[dev]"
```

Expected: installs without errors; `python -c "import fal_client; print('ok')"` prints `ok`.

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml backend/app/core/settings.py
git commit -m "feat: add fal-client dependency and fal_image_model setting"
```

---

### Task 2: Prompt builder, error class, and aspect-ratio helper

**Files:**
- Create: `backend/app/pipeline/agents/image_designer.py`
- Create: `backend/tests/test_image_designer.py`

**Interfaces:**
- Produces: `build_flux_prompt(blueprint: dict[str, Any]) -> str`
- Produces: `ImageGenerationError(Exception)`
- Produces: `_image_size(aspect_ratio: str) -> str | dict`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_image_designer.py`:

```python
import base64
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.agents.image_designer import (
    ImageGenerationError,
    _image_size,
    build_flux_prompt,
)

# Minimal valid base64 JPEG data URI for testing
_FAKE_DATA_URI = "data:image/jpeg;base64," + base64.b64encode(
    b"\xff\xd8\xff" + b"\x00" * 10
).decode()


def test_build_flux_prompt_all_fields():
    blueprint = {
        "subject": "amber glass serum bottle",
        "style": "editorial product photography",
        "lighting": "soft diffused studio light",
        "background": "white marble surface",
        "composition": "centered, shallow depth of field",
        "color_palette": "warm cream and amber tones",
        "camera_angle": "Studio Eye-Level",
        "lighting_preset": "Studio Softlight",
        "negative_prompts": "blurry, low quality",
        "aspect_ratio": "1:1",
    }
    result = build_flux_prompt(blueprint)
    assert "amber glass serum bottle" in result
    assert "editorial product photography" in result
    assert "soft diffused studio light" in result
    assert "white marble surface" in result
    assert "centered, shallow depth of field" in result
    assert "warm cream and amber tones" in result
    assert "Studio Eye-Level" in result
    assert "Studio Softlight" in result
    # negative_prompts must NOT appear in the main prompt
    assert "blurry" not in result


def test_build_flux_prompt_missing_optional_fields():
    blueprint = {
        "subject": "ceramic mug",
        "style": "minimalist",
        "lighting": "natural light",
        "background": "wooden table",
        "composition": "rule of thirds",
        "color_palette": "earth tones",
    }
    result = build_flux_prompt(blueprint)
    assert "ceramic mug" in result
    assert isinstance(result, str)
    assert len(result) > 10


def test_image_size_known_ratios():
    assert _image_size("1:1") == "square_hd"
    assert _image_size("16:9") == "landscape_16_9"
    assert _image_size("9:16") == "portrait_16_9"
    assert _image_size("4:5") == {"width": 864, "height": 1080}


def test_image_size_unknown_defaults_to_square():
    assert _image_size("unknown") == "square_hd"
    assert _image_size("") == "square_hd"


def test_image_generation_error_is_exception():
    err = ImageGenerationError("fal failed")
    assert isinstance(err, Exception)
    assert str(err) == "fal failed"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_image_designer.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.pipeline.agents.image_designer'`

- [ ] **Step 3: Create `image_designer.py` with the tested functions**

Create `backend/app/pipeline/agents/image_designer.py`:

```python
"""Image Designer Agent — FLUX prompt builder, fal.ai client, Refinement Agent."""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import time
from typing import Any

import anthropic
import httpx

from app.core.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_REFINEMENT_MODEL = "claude-sonnet-4-6"

_ASPECT_RATIO_MAP: dict[str, str | dict] = {
    "1:1": "square_hd",
    "16:9": "landscape_16_9",
    "9:16": "portrait_16_9",
    "4:5": {"width": 864, "height": 1080},
}


class ImageGenerationError(Exception):
    pass


def _image_size(aspect_ratio: str) -> str | dict:
    return _ASPECT_RATIO_MAP.get(aspect_ratio, "square_hd")


def build_flux_prompt(blueprint: dict[str, Any]) -> str:
    """Assemble creative_blueprint fields into a single FLUX prompt string."""
    core_parts = [
        blueprint.get("subject", ""),
        blueprint.get("style", ""),
        blueprint.get("lighting", ""),
        blueprint.get("background", ""),
        blueprint.get("composition", ""),
        blueprint.get("color_palette", ""),
    ]
    prompt = ". ".join(p for p in core_parts if p)
    if prompt and not prompt.endswith("."):
        prompt += "."
    if blueprint.get("camera_angle"):
        prompt += f" Camera: {blueprint['camera_angle']}."
    if blueprint.get("lighting_preset"):
        prompt += f" Lighting preset: {blueprint['lighting_preset']}."
    return prompt.strip()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_image_designer.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/agents/image_designer.py backend/tests/test_image_designer.py
git commit -m "feat: add image_designer prompt builder and ImageGenerationError"
```

---

### Task 3: `generate_image()` async fal.ai client

**Files:**
- Modify: `backend/app/pipeline/agents/image_designer.py`
- Modify: `backend/tests/test_image_designer.py`

**Interfaces:**
- Consumes: `settings.fal_image_model`, `settings.fal_api_key` (Task 1)
- Produces: `generate_image(prompt, image_data_uri, aspect_ratio, negative_prompts, seed) -> dict`
  - Returns `{"image_url": str, "seed": int | None, "latency_ms": int}`
  - Raises `ImageGenerationError` after 3 failed attempts

- [ ] **Step 1: Write failing tests for `generate_image`**

Add to `backend/tests/test_image_designer.py` (add `generate_image` to the existing import):

```python
from app.pipeline.agents.image_designer import (
    ImageGenerationError,
    _image_size,
    build_flux_prompt,
    generate_image,
)
from app.core.settings import settings
```

Then add these test functions:

```python
async def test_generate_image_success():
    fake_result = {
        "images": [{"url": "https://fal.media/files/abc/output.jpg"}],
        "seed": 42,
        "timings": {"inference": 3.1},
    }
    with patch("fal_client.upload", return_value="https://fal.storage/uploaded.jpg"), \
         patch("fal_client.run_async", new=AsyncMock(return_value=fake_result)):
        result = await generate_image(
            prompt="luxury serum bottle on marble",
            image_data_uri=_FAKE_DATA_URI,
            aspect_ratio="1:1",
            negative_prompts="blurry",
        )
    assert result["image_url"] == "https://fal.media/files/abc/output.jpg"
    assert result["seed"] == 42
    assert isinstance(result["latency_ms"], int)


async def test_generate_image_passes_seed():
    fake_result = {"images": [{"url": "https://fal.media/out.jpg"}], "seed": 99}
    with patch("fal_client.upload", return_value="https://fal.storage/img.jpg"), \
         patch("fal_client.run_async", new=AsyncMock(return_value=fake_result)) as mock_run:
        await generate_image(
            prompt="test",
            image_data_uri=_FAKE_DATA_URI,
            aspect_ratio="1:1",
            negative_prompts="",
            seed=99,
        )
    assert mock_run.call_args[1]["arguments"]["seed"] == 99


async def test_generate_image_retries_then_raises():
    with patch("fal_client.upload", return_value="https://fal.storage/img.jpg"), \
         patch("fal_client.run_async", new=AsyncMock(side_effect=RuntimeError("timeout"))), \
         patch("asyncio.sleep", new=AsyncMock()):
        with pytest.raises(ImageGenerationError, match="3 attempts"):
            await generate_image(
                prompt="test",
                image_data_uri=_FAKE_DATA_URI,
                aspect_ratio="1:1",
                negative_prompts="",
            )


async def test_generate_image_raises_if_no_images():
    fake_result = {"images": [], "seed": 1}
    with patch("fal_client.upload", return_value="https://fal.storage/img.jpg"), \
         patch("fal_client.run_async", new=AsyncMock(return_value=fake_result)), \
         patch("asyncio.sleep", new=AsyncMock()):
        with pytest.raises(ImageGenerationError):
            await generate_image(
                prompt="test",
                image_data_uri=_FAKE_DATA_URI,
                aspect_ratio="1:1",
                negative_prompts="",
            )


async def test_generate_image_no_fal_key_raises():
    with patch.object(settings, "fal_api_key", ""):
        os.environ.pop("FAL_KEY", None)
        with pytest.raises(ImageGenerationError, match="FAL_KEY"):
            await generate_image(
                prompt="test",
                image_data_uri=_FAKE_DATA_URI,
                aspect_ratio="1:1",
                negative_prompts="",
            )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_image_designer.py::test_generate_image_success tests/test_image_designer.py::test_generate_image_retries_then_raises -v
```

Expected: `ImportError` — `generate_image` not yet defined.

- [ ] **Step 3: Implement `generate_image` in `image_designer.py`**

Append to `backend/app/pipeline/agents/image_designer.py` after `build_flux_prompt`:

```python
def _ensure_fal_key() -> None:
    key = settings.fal_api_key or os.environ.get("FAL_KEY", "")
    if not key:
        raise ImageGenerationError(
            "FAL_KEY is not configured. Set fal_api_key in .env."
        )
    os.environ["FAL_KEY"] = key


async def generate_image(
    prompt: str,
    image_data_uri: str,
    aspect_ratio: str = "1:1",
    negative_prompts: str = "",
    seed: int | None = None,
) -> dict[str, Any]:
    """Submit an image-to-image job to fal.ai and return the result.

    Returns dict with keys: image_url (str), seed (int | None), latency_ms (int).
    Raises ImageGenerationError after 3 failed attempts.
    """
    import fal_client  # late import so tests can patch at the module level

    _ensure_fal_key()

    # Decode the base64 data URI to raw bytes, then upload to fal storage
    _, b64 = image_data_uri.split(",", 1)
    image_bytes = base64.b64decode(b64)
    image_url = fal_client.upload(image_bytes, "image/jpeg")

    arguments: dict[str, Any] = {
        "prompt": prompt,
        "image_url": image_url,
        "image_size": _image_size(aspect_ratio),
        "num_inference_steps": 28,
        "strength": 0.85,
        "num_images": 1,
    }
    if negative_prompts:
        arguments["negative_prompt"] = negative_prompts
    if seed is not None:
        arguments["seed"] = seed

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            start = time.monotonic()
            result = await fal_client.run_async(settings.fal_image_model, arguments=arguments)
            latency_ms = int((time.monotonic() - start) * 1000)

            images = result.get("images", [])
            if not images:
                raise ImageGenerationError("fal.ai returned no images in response")

            return {
                "image_url": images[0]["url"],
                "seed": result.get("seed"),
                "latency_ms": latency_ms,
            }
        except ImageGenerationError:
            raise
        except Exception as e:
            last_error = e
            logger.warning(f"fal.ai attempt {attempt + 1}/3 failed: {e}")
            if attempt < 2:
                await asyncio.sleep(2)

    raise ImageGenerationError(
        f"fal.ai failed after 3 attempts: {last_error}"
    ) from last_error
```

- [ ] **Step 4: Run all tests in the file**

```bash
cd backend && python -m pytest tests/test_image_designer.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/agents/image_designer.py backend/tests/test_image_designer.py
git commit -m "feat: add generate_image async fal.ai client with retry"
```

---

### Task 4: `rewrite_prompt()` Refinement Agent

**Files:**
- Modify: `backend/app/pipeline/agents/image_designer.py`
- Modify: `backend/tests/test_image_designer.py`

**Interfaces:**
- Produces: `rewrite_prompt(original_prompt: str, feedback: str, product_profile: dict) -> str`
  - Used by `revise.py` in Task 6

- [ ] **Step 1: Write failing tests for `rewrite_prompt`**

Add to `backend/tests/test_image_designer.py`:

```python
async def test_rewrite_prompt_returns_revised_string():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="revised prompt with darker background")]
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("anthropic.AsyncAnthropic", return_value=mock_client), \
         patch.object(settings, "anthropic_api_key", "test-key"):
        from app.pipeline.agents.image_designer import rewrite_prompt
        result = await rewrite_prompt(
            original_prompt="luxury serum on marble with soft lighting",
            feedback="make background darker and add rim lighting",
            product_profile={"product_name": "Serum X", "product_category": "skincare"},
        )

    assert isinstance(result, str)
    assert len(result) > 5
    mock_client.messages.create.assert_called_once()


async def test_rewrite_prompt_raises_if_no_anthropic_key():
    with patch.object(settings, "anthropic_api_key", ""):
        from app.pipeline.agents.image_designer import rewrite_prompt
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            await rewrite_prompt("prompt", "feedback", {})
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend && python -m pytest tests/test_image_designer.py::test_rewrite_prompt_returns_revised_string -v
```

Expected: `ImportError` — `rewrite_prompt` not yet defined.

- [ ] **Step 3: Implement `rewrite_prompt` in `image_designer.py`**

Append to `backend/app/pipeline/agents/image_designer.py`:

```python
_REFINEMENT_SYSTEM_PROMPT = """You are a creative director revising AI image generation prompts.
You receive an original prompt, user feedback requesting a change, and a product description.

Rules:
- Incorporate the user's requested change into the prompt.
- Remove any tokens that contradict the requested change.
- Preserve all product-description tokens: physical shape, label text, geometry, materials.
- Return ONLY the revised prompt string — no explanation, no preamble, no JSON."""


async def rewrite_prompt(
    original_prompt: str,
    feedback: str,
    product_profile: dict[str, Any],
) -> str:
    """Rewrite a FLUX prompt based on user feedback using Claude Sonnet."""
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    model = settings.prompt_model or DEFAULT_REFINEMENT_MODEL

    user_message = (
        f"Original prompt:\n{original_prompt}\n\n"
        f"User feedback: {feedback}\n\n"
        f"Product: {product_profile.get('product_name', '')} — "
        f"{product_profile.get('product_category', '')}"
    )

    response = await client.messages.create(
        model=model,
        max_tokens=500,
        system=_REFINEMENT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text.strip()
```

- [ ] **Step 4: Run all image designer tests**

```bash
cd backend && python -m pytest tests/test_image_designer.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/agents/image_designer.py backend/tests/test_image_designer.py
git commit -m "feat: add rewrite_prompt Refinement Agent"
```

---

### Task 5: LangGraph nodes + graph wiring

**Files:**
- Modify: `backend/app/pipeline/graph.py`
- Modify: `backend/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `build_flux_prompt()`, `generate_image()`, `ImageGenerationError` (Tasks 2–3)
- Produces: SSE events `image_generation_started`, `image_generation_complete`, `image_generation_failed`, `image_generation_skipped`
- Produces: updated `PipelineState` with `image_generation_skipped: bool` field

- [ ] **Step 1: Write failing pipeline tests**

Add to `backend/tests/test_pipeline.py` (add these imports at the top if not present):

```python
import json
from unittest.mock import AsyncMock, MagicMock, patch
```

Then add these test functions:

```python
async def test_pipeline_image_generation_complete(tmp_content_dir):
    run_id = _make_run(tmp_content_dir)
    fake_fal_result = {
        "images": [{"url": "https://fal.media/files/out.jpg"}],
        "seed": 77,
    }
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20

    with patch("app.pipeline.agents.vision_orchestrator.get_orchestrator") as mock_orch, \
         patch("app.pipeline.agents.summary_agent.generate_summary_card",
               new=AsyncMock(return_value={"product_name": "Test", "vision_available": False})), \
         patch("app.pipeline.agents.summary_agent.generate_image_prompt",
               new=AsyncMock(return_value={
                   "subject": "test bottle", "style": "editorial", "lighting": "soft",
                   "background": "white", "composition": "centered", "color_palette": "cream",
                   "camera_angle": "eye-level", "aspect_ratio": "1:1",
                   "negative_prompts": "", "lighting_preset": "Studio Softlight",
               })), \
         patch("fal_client.upload", return_value="https://fal.storage/img.jpg"), \
         patch("fal_client.run_async", new=AsyncMock(return_value=fake_fal_result)), \
         patch("app.pipeline.agents.image_designer.settings") as mock_img_settings, \
         patch("httpx.AsyncClient") as mock_httpx:
        mock_orch.return_value.analyze = AsyncMock(return_value=None)
        mock_img_settings.fal_api_key = "test-key"
        mock_img_settings.fal_image_model = "fal-ai/flux/dev/image-to-image"
        mock_img_settings.anthropic_api_key = "test-key"
        mock_img_settings.prompt_model = "claude-sonnet-4-6"
        mock_httpx.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock(get=AsyncMock(return_value=MagicMock(content=fake_png)))
        )
        mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)
        events = await _collect(run_id)

    names = [e["event"] for e in events]
    assert "image_generation_started" in names
    assert "image_generation_complete" in names
    assert "image_generation_failed" not in names

    complete = next(e for e in events if e["event"] == "image_generation_complete")
    assert complete["data"]["iteration"] == 1
    assert complete["data"]["image_path"] == "v1.png"
    assert f"/api/runs/{run_id}/images/v1.png" == complete["data"]["image_url"]

    assert (tmp_content_dir / run_id / "v1.png").exists()
    meta = run_manager.get_metadata(run_id)
    assert meta["status"] == "image_generated"
    assert len(meta["image_iterations"]) == 1


async def test_pipeline_image_generation_failed_routes_to_end(tmp_content_dir):
    run_id = _make_run(tmp_content_dir)

    with patch("app.pipeline.agents.vision_orchestrator.get_orchestrator") as mock_orch, \
         patch("app.pipeline.agents.summary_agent.generate_summary_card",
               new=AsyncMock(return_value={"product_name": "Test", "vision_available": False})), \
         patch("app.pipeline.agents.summary_agent.generate_image_prompt",
               new=AsyncMock(return_value={
                   "subject": "bottle", "style": "photo", "lighting": "soft",
                   "background": "white", "composition": "center", "color_palette": "cream",
                   "camera_angle": "eye-level", "aspect_ratio": "1:1",
                   "negative_prompts": "", "lighting_preset": "Studio Softlight",
               })), \
         patch("fal_client.upload", return_value="https://fal.storage/img.jpg"), \
         patch("fal_client.run_async", new=AsyncMock(side_effect=RuntimeError("fal down"))), \
         patch("asyncio.sleep", new=AsyncMock()), \
         patch("app.pipeline.agents.image_designer.settings") as mock_img_settings:
        mock_orch.return_value.analyze = AsyncMock(return_value=None)
        mock_img_settings.fal_api_key = "test-key"
        mock_img_settings.fal_image_model = "fal-ai/flux/dev/image-to-image"
        mock_img_settings.anthropic_api_key = "test-key"
        mock_img_settings.prompt_model = "claude-sonnet-4-6"
        events = await _collect(run_id)

    names = [e["event"] for e in events]
    assert "image_generation_failed" in names
    assert "pipeline_complete" not in names
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend && python -m pytest tests/test_pipeline.py::test_pipeline_image_generation_complete tests/test_pipeline.py::test_pipeline_image_generation_failed_routes_to_end -v
```

Expected: FAIL — nodes not yet added to graph.

- [ ] **Step 3: Update `PipelineState` and `run_pipeline` in `graph.py`**

In `backend/app/pipeline/graph.py`, update `PipelineState`:

```python
class PipelineState(TypedDict):
    run_id: str
    events: list[dict]
    results: dict
    failed: bool
    image_generation_skipped: bool
```

Update `run_pipeline` to initialise the new field:

```python
async def run_pipeline(run_id: str) -> AsyncGenerator[dict, None]:
    state: PipelineState = {
        "run_id": run_id,
        "events": [],
        "results": {},
        "failed": False,
        "image_generation_skipped": False,
    }
    async for chunk in pipeline.astream(state, stream_mode="updates"):
        for node_update in chunk.values():
            new_events = node_update.get("events", [])
            if new_events:
                yield new_events[-1]
```

- [ ] **Step 4: Add imports to `graph.py`**

Add to the imports section of `backend/app/pipeline/graph.py`:

```python
import httpx

from app.pipeline.agents.image_designer import (
    ImageGenerationError,
    build_flux_prompt,
    generate_image,
)
```

- [ ] **Step 5: Add the two new node functions to `graph.py`**

Add after `summary_agent_node` in `backend/app/pipeline/graph.py`:

```python
def image_designer_start_node(state: PipelineState) -> dict:
    """Validate blueprint presence and emit the started event (instant, non-blocking)."""
    creative_blueprint = state["results"].get("creative_blueprint")
    if not creative_blueprint:
        return _emit(
            state,
            "image_generation_skipped",
            {"reason": "No creative blueprint — summary agent may have failed"},
            image_generation_skipped=True,
        )
    return _emit(
        state,
        "image_generation_started",
        {"model": settings.fal_image_model},
        image_generation_skipped=False,
    )


async def image_designer_node(state: PipelineState) -> dict:
    """Call fal.ai FLUX, download the output image, save to disk."""
    run_id = state["run_id"]
    creative_blueprint = state["results"]["creative_blueprint"]
    image_payload = state["results"]["image"]["image_payload"]

    prompt = build_flux_prompt(creative_blueprint)
    aspect_ratio = creative_blueprint.get("aspect_ratio", "1:1")
    negative_prompts = creative_blueprint.get("negative_prompts", "")

    try:
        fal_result = await generate_image(
            prompt=prompt,
            image_data_uri=image_payload,
            aspect_ratio=aspect_ratio,
            negative_prompts=negative_prompts,
        )
    except ImageGenerationError as e:
        run_manager.update_metadata(run_id, {"status": "failed"})
        return _emit(
            state,
            "image_generation_failed",
            {"error": str(e), "retries": 2},
            failed=True,
        )

    output_path = run_manager.get_content_dir() / run_id / "v1.png"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(fal_result["image_url"])
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
    except Exception as e:
        run_manager.update_metadata(run_id, {"status": "failed"})
        return _emit(
            state,
            "image_generation_failed",
            {"error": f"Failed to save generated image: {e}", "retries": 2},
            failed=True,
        )

    iteration_entry = {
        "iteration": 1,
        "prompt": prompt,
        "seed": fal_result.get("seed"),
        "output_path": "v1.png",
        "feedback": None,
    }
    run_manager.update_metadata(
        run_id,
        {"status": "image_generated", "image_iterations": [iteration_entry]},
    )

    image_url = f"/api/runs/{run_id}/images/v1.png"
    results = {**state["results"], "image_generation": fal_result}
    return _emit(
        state,
        "image_generation_complete",
        {
            "iteration": 1,
            "image_path": "v1.png",
            "image_url": image_url,
            "prompt_used": prompt,
            "seed": fal_result.get("seed"),
        },
        results=results,
    )
```

- [ ] **Step 6: Add routing functions and wire the graph in `graph.py`**

Add routing functions after `_route_after_image`:

```python
def _route_after_image_designer_start(state: PipelineState) -> str:
    return "complete" if state["image_generation_skipped"] else "image_designer"


def _route_after_image_designer(state: PipelineState) -> str:
    return END if state["failed"] else "complete"
```

Replace `build_graph()` with the full updated version:

```python
def build_graph():
    builder = StateGraph(PipelineState)
    builder.add_node("start", start_node)
    builder.add_node("process_text", process_text_node)
    builder.add_node("process_image", process_image_node)
    builder.add_node("process_reference", process_reference_node)
    builder.add_node("process_video", process_video_node)
    builder.add_node("process_model", process_model_node)
    builder.add_node("finalize", finalize_node)
    builder.add_node("vision_analysis", vision_analysis_node)
    builder.add_node("summary_agent", summary_agent_node)
    builder.add_node("image_designer_start", image_designer_start_node)
    builder.add_node("image_designer", image_designer_node)
    builder.add_node("complete", complete_node)

    builder.set_entry_point("start")
    builder.add_edge("start", "process_text")
    builder.add_edge("process_text", "process_image")
    builder.add_conditional_edges(
        "process_image",
        _route_after_image,
        {"process_reference": "process_reference", END: END},
    )
    builder.add_edge("process_reference", "process_video")
    builder.add_edge("process_video", "process_model")
    builder.add_edge("process_model", "finalize")
    builder.add_edge("finalize", "vision_analysis")
    builder.add_edge("vision_analysis", "summary_agent")
    builder.add_edge("summary_agent", "image_designer_start")
    builder.add_conditional_edges(
        "image_designer_start",
        _route_after_image_designer_start,
        {"image_designer": "image_designer", "complete": "complete"},
    )
    builder.add_conditional_edges(
        "image_designer",
        _route_after_image_designer,
        {"complete": "complete", END: END},
    )
    builder.add_edge("complete", END)
    return builder.compile()
```

- [ ] **Step 7: Update existing pipeline tests to mock the new agents**

The existing tests in `test_pipeline.py` that call `_collect()` will now reach the new nodes and fail unless patched. For each existing test that runs the pipeline, add the same vision/summary/image-gen patches. Replace `test_pipeline_text_and_image_no_video` with:

```python
async def test_pipeline_text_and_image_no_video(tmp_content_dir: Path):
    run_id = _make_run(tmp_content_dir)
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20

    with patch("app.pipeline.agents.vision_orchestrator.get_orchestrator") as mock_orch, \
         patch("app.pipeline.agents.summary_agent.generate_summary_card",
               new=AsyncMock(return_value={"product_name": "Test", "vision_available": False})), \
         patch("app.pipeline.agents.summary_agent.generate_image_prompt",
               new=AsyncMock(return_value={
                   "subject": "bottle", "style": "photo", "lighting": "soft",
                   "background": "white", "composition": "center", "color_palette": "cream",
                   "camera_angle": "eye-level", "aspect_ratio": "1:1",
                   "negative_prompts": "", "lighting_preset": "Studio Softlight",
               })), \
         patch("fal_client.upload", return_value="https://fal.storage/img.jpg"), \
         patch("fal_client.run_async", new=AsyncMock(return_value={
             "images": [{"url": "https://fal.media/out.jpg"}], "seed": 1,
         })), \
         patch("app.pipeline.agents.image_designer.settings") as mock_img_settings, \
         patch("httpx.AsyncClient") as mock_httpx:
        mock_orch.return_value.analyze = AsyncMock(return_value=None)
        mock_img_settings.fal_api_key = "test-key"
        mock_img_settings.fal_image_model = "fal-ai/flux/dev/image-to-image"
        mock_httpx.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock(get=AsyncMock(return_value=MagicMock(content=fake_png)))
        )
        mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)
        events = await _collect(run_id)

    names = [e["event"] for e in events]
    assert "pipeline_started" in names
    assert "text_processed" in names
    assert "image_processed" in names
    assert "ingestion_complete" in names
    assert "image_generation_started" in names
    assert "image_generation_complete" in names
    assert "pipeline_complete" in names

    artifact = json.loads(
        (tmp_content_dir / run_id / "processed" / "ingestion.json").read_text()
    )
    assert artifact["image"]["image_payload"].startswith("data:image/jpeg;base64,")
```

Apply the same patch pattern to any other existing pipeline tests that call `_collect()`.

- [ ] **Step 8: Run the full test suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 9: Lint**

```bash
cd backend && ruff check app tests
```

Expected: no errors.

- [ ] **Step 10: Commit**

```bash
git add backend/app/pipeline/graph.py backend/tests/test_pipeline.py
git commit -m "feat: add image_designer nodes to pipeline graph"
```

---

### Task 6: Revision endpoint + image serving

**Files:**
- Create: `backend/app/api/routes/revise.py`
- Create: `backend/tests/test_revise.py`
- Create: `backend/tests/test_image_serving.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `rewrite_prompt()`, `generate_image()`, `ImageGenerationError` (Tasks 3–4)
- Consumes: `run_manager.get_metadata()`, `run_manager.update_metadata()`
- Produces: `POST /api/runs/{run_id}/revise` → `{"iteration", "image_path", "image_url", "prompt_used", "seed"}`
- Produces: `GET /api/runs/{run_id}/images/{filename}` → PNG/JPEG bytes

- [ ] **Step 1: Write failing tests for the revision endpoint**

Create `backend/tests/test_revise.py`:

```python
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
```

- [ ] **Step 2: Write failing tests for image serving**

Create `backend/tests/test_image_serving.py`:

```python
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
```

- [ ] **Step 3: Run to confirm failure**

```bash
cd backend && python -m pytest tests/test_revise.py tests/test_image_serving.py -v
```

Expected: 404 or connection errors — routes not yet registered.

- [ ] **Step 4: Create `backend/app/api/routes/revise.py`**

```python
"""Revision endpoint — POST /api/runs/{run_id}/revise
   Image serving   — GET  /api/runs/{run_id}/images/{filename}
"""

from __future__ import annotations

import json
import logging
import mimetypes
import re
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.run_manager import run_manager
from app.core.settings import settings
from app.pipeline.agents.image_designer import ImageGenerationError, generate_image, rewrite_prompt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/runs", tags=["revise"])

_UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
MAX_ITERATIONS = 10


def _validate_run_dir(run_id: str) -> Path:
    if not _UUID4_RE.match(run_id):
        raise HTTPException(status_code=404, detail="Run not found.")
    run_dir = (settings.content_dir / run_id).resolve()
    if not run_dir.is_relative_to(settings.content_dir.resolve()) or not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found.")
    return run_dir


class ReviseRequest(BaseModel):
    feedback: str
    iteration: int


@router.post("/{run_id}/revise")
async def revise_image(run_id: str, body: ReviseRequest) -> dict:
    run_dir = _validate_run_dir(run_id)

    if body.iteration >= MAX_ITERATIONS:
        raise HTTPException(status_code=400, detail="max_iterations_reached")

    metadata = run_manager.get_metadata(run_id)
    image_iterations = metadata.get("image_iterations", [])
    if not image_iterations:
        raise HTTPException(status_code=400, detail="No image iterations found for this run.")

    last_prompt = image_iterations[-1]["prompt"]
    product_profile = metadata.get("agent_states", {}).get("product_profile") or {}

    ingestion_path = run_dir / "processed" / "ingestion.json"
    if not ingestion_path.exists():
        raise HTTPException(status_code=400, detail="Ingestion data not available.")
    ingestion = json.loads(ingestion_path.read_text())
    image_data_uri = ingestion.get("image", {}).get("image_payload", "")
    if not image_data_uri:
        raise HTTPException(status_code=400, detail="Product image payload not found.")

    steering = metadata.get("steering") or {}
    aspect_ratio = steering.get("aspect_ratio") or "1:1"
    negative_prompts = steering.get("negative_prompts") or ""

    try:
        revised_prompt = await rewrite_prompt(last_prompt, body.feedback, product_profile)
    except Exception as e:
        logger.error(f"Refinement agent failed for run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Refinement agent error: {e}") from e

    try:
        fal_result = await generate_image(
            prompt=revised_prompt,
            image_data_uri=image_data_uri,
            aspect_ratio=aspect_ratio,
            negative_prompts=negative_prompts,
        )
    except (ImageGenerationError, Exception) as e:
        logger.error(f"Image generation failed for run {run_id} revision: {e}")
        raise HTTPException(status_code=500, detail=f"Image generation error: {e}") from e

    new_iteration = body.iteration + 1
    output_filename = f"v{new_iteration}.png"
    output_path = run_dir / output_filename

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(fal_result["image_url"])
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
    except Exception as e:
        logger.error(f"Failed to save revised image for run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save image: {e}") from e

    new_entry = {
        "iteration": new_iteration,
        "prompt": revised_prompt,
        "seed": fal_result.get("seed"),
        "output_path": output_filename,
        "feedback": body.feedback,
    }
    run_manager.update_metadata(
        run_id, {"image_iterations": image_iterations + [new_entry]}
    )

    return {
        "iteration": new_iteration,
        "image_path": output_filename,
        "image_url": f"/api/runs/{run_id}/images/{output_filename}",
        "prompt_used": revised_prompt,
        "seed": fal_result.get("seed"),
    }


@router.get("/{run_id}/images/{filename}")
async def serve_image(run_id: str, filename: str) -> FileResponse:
    run_dir = _validate_run_dir(run_id)

    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file extension.")

    file_path = (run_dir / filename).resolve()
    if not file_path.is_relative_to(run_dir):
        raise HTTPException(status_code=400, detail="Invalid filename.")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found.")

    media_type = mimetypes.guess_type(file_path.name)[0] or "image/png"
    return FileResponse(file_path, media_type=media_type)
```

- [ ] **Step 5: Register the revise router in `main.py`**

Replace `backend/app/main.py` with:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import revise, runs, settings as settings_router, sse, uploads
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
app.include_router(settings_router.router)
app.include_router(sse.router)
app.include_router(uploads.router)
app.include_router(revise.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 6: Run revision + serving tests**

```bash
cd backend && python -m pytest tests/test_revise.py tests/test_image_serving.py -v
```

Expected: all tests PASS.

- [ ] **Step 7: Run full test suite + lint**

```bash
cd backend && python -m pytest tests/ -v && ruff check app tests
```

Expected: all PASS, no lint errors.

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/routes/revise.py backend/app/main.py backend/tests/test_revise.py backend/tests/test_image_serving.py
git commit -m "feat: add revision endpoint and image serving route"
```

---

### Task 7: `ImageWorkspace.tsx` frontend component + CSS

**Files:**
- Create: `frontend/components/dashboard/ImageWorkspace.tsx`
- Modify: `frontend/components/dashboard/dashboard.css`

**Interfaces:**
- Consumes props: `runId: string`, `initialImageUrl: string`, `initialIteration: number`, `initialPrompt: string`, `initialSeed: number | null`
- Produces: self-contained component; calls `POST /api/runs/{runId}/revise`

- [ ] **Step 1: Append image-workspace CSS to `dashboard.css`**

Add at the end of `frontend/components/dashboard/dashboard.css`:

```css
/* ---------- Image Workspace (inline revision panel) ---------- */
.pp-dash .image-workspace {
  margin-top: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  border-top: 1px solid var(--border);
  padding-top: var(--space-4);
}
.pp-dash .image-workspace-preview {
  width: 100%;
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  object-fit: contain;
  background: var(--surface);
  max-height: 480px;
}
.pp-dash .image-workspace-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: var(--muted-fg);
}
.pp-dash .image-workspace-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.pp-dash .image-workspace-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--fg);
}
.pp-dash .image-workspace-input {
  width: 100%;
  min-height: 72px;
  padding: var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  color: var(--fg);
  font-size: 14px;
  font-family: var(--font-body);
  resize: vertical;
}
.pp-dash .image-workspace-input:focus {
  outline: none;
  border-color: var(--primary);
}
.pp-dash .image-workspace-input:disabled { opacity: 0.5; cursor: not-allowed; }
.pp-dash .image-workspace-actions { display: flex; gap: var(--space-3); align-items: center; }
.pp-dash .image-workspace-error {
  font-size: 13px;
  color: var(--destructive);
  padding: var(--space-2) var(--space-3);
  background: rgba(var(--destructive-rgb), 0.07);
  border-radius: var(--radius-sm);
}
.pp-dash .image-workspace-done {
  font-size: 14px;
  color: var(--green);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.pp-dash .image-workspace-max {
  font-size: 13px;
  color: var(--muted-fg);
  font-style: italic;
}
```

- [ ] **Step 2: Create `ImageWorkspace.tsx`**

Create `frontend/components/dashboard/ImageWorkspace.tsx`:

```tsx
"use client";

import { useState } from "react";
import { CheckIcon } from "./icons";

interface Props {
  runId: string;
  initialImageUrl: string;
  initialIteration: number;
  initialPrompt: string;
  initialSeed: number | null;
}

type Status = "idle" | "submitting" | "error";

export function ImageWorkspace({
  runId,
  initialImageUrl,
  initialIteration,
}: Props) {
  const [imageSrc, setImageSrc] = useState(initialImageUrl);
  const [iteration, setIteration] = useState(initialIteration);
  const [feedback, setFeedback] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [approved, setApproved] = useState(false);

  const maxReached = iteration >= 10;

  async function handleRevise() {
    if (!feedback.trim() || status === "submitting") return;
    setStatus("submitting");
    setErrorMsg("");

    try {
      const resp = await fetch(`/api/runs/${runId}/revise`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ feedback: feedback.trim(), iteration }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: "Unknown error" }));
        if (resp.status === 400 && err.detail === "max_iterations_reached") {
          setIteration(10);
          setStatus("idle");
          return;
        }
        throw new Error(err.detail ?? `HTTP ${resp.status}`);
      }

      const data = await resp.json();
      setImageSrc(data.image_url);
      setIteration(data.iteration);
      setFeedback("");
      setStatus("idle");
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Revision failed. Please try again."
      );
      setStatus("error");
    }
  }

  async function handleApprove() {
    try {
      const resp = await fetch(imageSrc);
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `pixpilot_v${iteration}.png`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Download failed — image still visible, user can right-click save
    }
    setApproved(true);
  }

  return (
    <div className="image-workspace">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        className="image-workspace-preview"
        src={imageSrc}
        alt={`Generated product image iteration ${iteration}`}
      />

      <div className="image-workspace-meta">
        <span>Iteration {iteration} of 10</span>
      </div>

      {approved ? (
        <div className="image-workspace-done">
          <CheckIcon style={{ width: 16, height: 16 }} />
          Image downloaded — run complete.
        </div>
      ) : maxReached ? (
        <p className="image-workspace-max">
          Maximum revisions reached — approve the image above or start a new run.
        </p>
      ) : (
        <div className="image-workspace-form">
          <label className="image-workspace-label">What would you like to change?</label>
          <textarea
            className="image-workspace-input"
            placeholder="e.g. Make the background darker and add golden rim lighting"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            disabled={status === "submitting"}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void handleRevise();
            }}
          />
          {status === "error" && (
            <div className="image-workspace-error">{errorMsg}</div>
          )}
          <div className="image-workspace-actions">
            <button
              className="btn btn-outline btn-sm"
              onClick={() => void handleRevise()}
              disabled={status === "submitting" || !feedback.trim()}
            >
              {status === "submitting" ? (
                <><span className="btn-spin" /> Generating…</>
              ) : (
                "Submit Revision"
              )}
            </button>
            <button
              className="btn btn-default btn-sm"
              onClick={() => void handleApprove()}
              disabled={status === "submitting"}
            >
              Approve &amp; Download
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors in `ImageWorkspace.tsx`.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/dashboard/ImageWorkspace.tsx frontend/components/dashboard/dashboard.css
git commit -m "feat: add ImageWorkspace component and CSS"
```

---

### Task 8: Wire `ImageWorkspace` into `RunView.tsx`

**Files:**
- Modify: `frontend/components/dashboard/RunView.tsx`

**Interfaces:**
- Consumes: `ImageWorkspace` (Task 7)
- Consumes: `image_generation_complete` SSE event `data: {image_url, iteration, prompt_used, seed}`

- [ ] **Step 1: Replace `PIPELINE_STAGES` and add `ImageWorkspace` import**

Replace the entire contents of `frontend/components/dashboard/RunView.tsx` with:

```tsx
"use client";

import { useEffect, useRef } from "react";
import { useSSE } from "@/lib/sse";
import { StageTracker, type Stage } from "./StageTracker";
import { type RunMeta } from "./NewGenerationModal";
import { CheckIcon, XIcon } from "./icons";
import { ImageWorkspace } from "./ImageWorkspace";

const PIPELINE_STAGES: { key: string; name: string; label: string }[] = [
  { key: "text_processed",            name: "Text",       label: "1" },
  { key: "image_processed",           name: "Image",      label: "2" },
  { key: "video_processed",           name: "Media",      label: "3" },
  { key: "model_processed",           name: "3D Model",   label: "4" },
  { key: "ingestion_complete",        name: "Ingestion",  label: "5" },
  { key: "vision_analyzed",           name: "Vision",     label: "6" },
  { key: "summary_complete",          name: "Summary",    label: "7" },
  { key: "image_generation_started",  name: "Generating", label: "8" },
  { key: "image_generation_complete", name: "Done",       label: "9" },
];

const MODE_LABELS: Record<string, string> = {
  ecommerce: "E-Commerce Batch",
  social:    "Social Media",
  ab:        "A/B Exploration",
  seasonal:  "Seasonal Campaign",
  summarize: "Summarization",
};

function deriveStages(seenEvents: Set<string>): Stage[] {
  let foundActive = false;
  return PIPELINE_STAGES.map((s, i) => {
    if (seenEvents.has(s.key)) return { name: s.name, meta: "done", state: "done" as const };
    const prevDone = i === 0 || seenEvents.has(PIPELINE_STAGES[i - 1].key);
    if (!foundActive && prevDone) {
      foundActive = true;
      return { name: s.name, meta: "in progress", state: "active" as const, label: s.label };
    }
    return { name: s.name, meta: "pending", state: "pending" as const, label: s.label };
  });
}

export function RunView({ run, onDismiss }: { run: RunMeta; onDismiss: () => void }) {
  const { messages } = useSSE(run.runId);
  const logRef = useRef<HTMLDivElement>(null);

  const seenEvents = new Set(messages.map((m) => m.event));
  const stages = deriveStages(seenEvents);

  const isComplete = seenEvents.has("pipeline_complete");
  const hasError   = seenEvents.has("pipeline_error") || seenEvents.has("image_generation_failed");
  const isTerminal = isComplete || hasError || seenEvents.has("stream_end");

  const imageCompleteMsg = messages.find((m) => m.event === "image_generation_complete");
  const imageData = imageCompleteMsg?.data as {
    image_url: string;
    iteration: number;
    prompt_used: string;
    seed: number | null;
  } | undefined;

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="run-view">
      <div className="run-head">
        <div>
          <h1 className="heading-2">{run.name}</h1>
          <span className="badge badge-outline" style={{ marginTop: 4, display: "inline-flex" }}>
            {MODE_LABELS[run.mode] ?? run.mode}
          </span>
        </div>
        {isTerminal && (
          <button className="btn btn-ghost" onClick={onDismiss}>
            <XIcon /> Dismiss
          </button>
        )}
      </div>

      <div className="card run-stage-card">
        <div className="run-stage-head">
          {isComplete && (
            <span className="badge badge-success">
              <span className="pulse" />
              <CheckIcon style={{ width: 12, height: 12 }} /> Complete
            </span>
          )}
          {hasError && (
            <span className="badge badge-error">
              <XIcon style={{ width: 12, height: 12 }} /> Failed
            </span>
          )}
          {!isTerminal && (
            <span className="badge badge-amber"><span className="pulse" /> Running</span>
          )}
        </div>
        <StageTracker stages={stages} bare />
      </div>

      <div className="run-body">
        <div className="run-inputs card">
          <div className="run-inputs-head">Inputs</div>
          {run.imagePreviewUrl ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img className="run-product-img" src={run.imagePreviewUrl} alt="Product" />
          ) : (
            <div className="run-product-placeholder">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" />
                <polyline points="21 15 16 10 5 21" />
              </svg>
            </div>
          )}
          <div className="run-inputs-meta">
            <div className="run-input-row">
              <span className="overline">Generation</span>
              <span className="body-s" style={{ fontWeight: 500 }}>{run.name}</span>
            </div>
            <div className="run-input-row">
              <span className="overline">Mode</span>
              <span className="body-s">{MODE_LABELS[run.mode] ?? run.mode}</span>
            </div>
            <div className="run-input-row">
              <span className="overline">Run ID</span>
              <span className="caption" style={{ fontFamily: "monospace", wordBreak: "break-all" }}>{run.runId}</span>
            </div>
          </div>
        </div>

        <div className="run-log card">
          <div className="run-log-head">Live Events</div>
          <div className="run-log-body" ref={logRef}>
            {messages.length === 0 && (
              <div className="run-log-empty">
                <span className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
                Waiting for pipeline events…
              </div>
            )}
            {messages.map((msg, i) => {
              if (msg.event === "summary_complete" && msg.data.summary_card) {
                const card = msg.data.summary_card as Record<string, unknown>;
                return (
                  <div key={i} className="log-item log-summary-card">
                    <div className="summary-card-title">
                      <span className="log-event">summary_complete</span>
                      <span className="badge badge-success" style={{ fontSize: 10, padding: "1px 6px" }}>
                        {card.vision_available ? "Vision" : "Text-only"}
                      </span>
                    </div>
                    <div className="summary-card-body">
                      <div className="summary-card-header">
                        <span className="summary-product-name">{String(card.product_name ?? "")}</span>
                        {!!card.product_category && (
                          <span className="caption" style={{ color: "var(--text-muted)" }}>{String(card.product_category)}</span>
                        )}
                      </div>
                      {Array.isArray(card.key_features) && card.key_features.length > 0 && (
                        <div className="summary-row">
                          <span className="overline">Features</span>
                          <span className="body-s">{(card.key_features as string[]).join(" · ")}</span>
                        </div>
                      )}
                      {!!card.target_audience && (
                        <div className="summary-row">
                          <span className="overline">Audience</span>
                          <span className="body-s">{String(card.target_audience)}</span>
                        </div>
                      )}
                      {Array.isArray(card.dominant_colors) && card.dominant_colors.length > 0 && (
                        <div className="summary-row">
                          <span className="overline">Colors</span>
                          <span className="summary-swatches">
                            {(card.dominant_colors as string[]).map((hex) => (
                              <span key={hex} className="summary-swatch-item">
                                <span className="summary-swatch" style={{ background: hex }} />
                                <span className="caption">{hex}</span>
                              </span>
                            ))}
                          </span>
                        </div>
                      )}
                      {Array.isArray(card.materials) && card.materials.length > 0 && (
                        <div className="summary-row">
                          <span className="overline">Materials</span>
                          <span className="body-s">{(card.materials as string[]).join(", ")}</span>
                        </div>
                      )}
                      {!!card.style_vibe && (
                        <div className="summary-row">
                          <span className="overline">Style Vibe</span>
                          <span className="body-s" style={{ fontStyle: "italic" }}>{String(card.style_vibe)}</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              }

              if (msg.event === "image_generation_complete" && imageData) {
                return (
                  <div key={i} className="log-item log-ok">
                    <span className="log-event">image_generation_complete</span>
                    <span className="log-data">
                      iteration: {imageData.iteration} · seed: {imageData.seed ?? "—"}
                    </span>
                    <ImageWorkspace
                      runId={run.runId}
                      initialImageUrl={imageData.image_url}
                      initialIteration={imageData.iteration}
                      initialPrompt={imageData.prompt_used}
                      initialSeed={imageData.seed}
                    />
                  </div>
                );
              }

              return (
                <div
                  key={i}
                  className={`log-item ${
                    msg.event.includes("error") || msg.event.includes("failed")
                      ? "log-error"
                      : msg.event === "pipeline_complete"
                      ? "log-ok"
                      : ""
                  }`}
                >
                  <span className="log-event">{msg.event}</span>
                  {Object.keys(msg.data).length > 0 && (
                    <span className="log-data">
                      {Object.entries(msg.data)
                        .filter(([k]) => k !== "run_id" && k !== "summary_card")
                        .slice(0, 3)
                        .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`)
                        .join(" · ")}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
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
git add frontend/components/dashboard/RunView.tsx
git commit -m "feat: wire ImageWorkspace into RunView SSE event log"
```

---

## Spec Coverage

| Spec requirement | Task |
|---|---|
| FLUX prompt from `creative_blueprint` | Task 2 `build_flux_prompt()` |
| fal.ai image-to-image async | Task 3 `generate_image()` with `run_async` |
| 2 retries on fal failure (3 total attempts) | Task 3 retry loop |
| `image_generation_started` SSE event | Task 5 `image_designer_start_node` |
| `image_generation_complete` SSE event | Task 5 `image_designer_node` |
| `image_generation_failed` → run failed, routes to END | Task 5 |
| `image_generation_skipped` when no blueprint | Task 5 `image_designer_start_node` |
| Save to `content/<run_id>/v1.png` | Task 5 `image_designer_node` |
| `image_iterations` written to `run_metadata.json` | Tasks 5 and 6 |
| `POST /api/runs/{run_id}/revise` | Task 6 |
| Max 10 iterations guard → HTTP 400 | Task 6 |
| Refinement Agent rewrites prompt (Claude Sonnet) | Task 4 `rewrite_prompt()` |
| Load product image from `ingestion.json` for revisions | Task 6 |
| `GET /api/runs/{run_id}/images/{filename}` | Task 6 `serve_image()` |
| Path traversal rejection | Task 6 (`is_relative_to` guard) |
| Extension allowlist for image serving | Task 6 `_ALLOWED_EXTENSIONS` |
| `ImageWorkspace` inline in event log | Tasks 7–8 |
| Approve & Download | Task 7 `handleApprove()` |
| Max iterations UI message | Task 7 |
| `PIPELINE_STAGES` updated to include generation stages | Task 8 |
| All fal calls mocked in tests | Tasks 3, 5, 6 |
