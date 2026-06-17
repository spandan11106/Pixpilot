# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pixpilot is a self-hosted pipeline that turns a product image + description into marketing
images and copy using a coordinated set of AI agents. This repo currently implements the
**ingestion stage**: it validates uploads and preprocesses every input (text, image, video,
3D model) into clean, base64 payloads suitable for vision-model consumption. Downstream agent
stages (Vision, Research, Image Designer) are tracked in `.claude/PRD_v1_Image_Pipeline.md`.

## Rules

- All agent instruction files (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, etc.) must live exclusively
  inside `.claude/`. Never create or leave these files anywhere else in the repository.

## Repository Layout

- **`backend/`** — FastAPI app (`app/`) with the LangGraph ingestion pipeline. This is the
  primary service.
- **`frontend/`** — Next.js submission form (mode selector, file uploads, supervision panel).
- **`services/ffmpeg/`** — FastAPI sidecar that extracts video keyframes (`POST /extract-frames`).
- **`services/renderer/`** — Node + Three.js sidecar that renders 4 perspective thumbnails of a
  3D model (`POST /render-3d`).
- **`data_processing/`** + **`testing/`** — legacy standalone `image.py` / `text.py` modules and
  their script-based tests. The backend's processors mirror these; prefer editing the backend
  copies for pipeline work.
- **`content/`** — runtime storage. Each run lives in `content/<run_id>/` with `inputs/`,
  `processed/`, and `run_metadata.json`. Do not commit run data.
- **`docker-compose.yml`** — orchestrates backend (8000), frontend (3000), ffmpeg (8001),
  renderer (8002). All four share the `./content` mount.

## Backend Architecture

**Pipeline** (`backend/app/pipeline/graph.py`) — a LangGraph that streams SSE events:

```
start → process_text → process_image → process_video → process_model → finalize → complete
```

The product **image is required**: a missing/failed image halts the run with a `pipeline_error`.
**Video and 3D model are optional and non-fatal**: missing/failed inputs emit `*_skipped` /
`*_failed` and the run continues. `finalize` writes full payloads to
`content/<run_id>/processed/ingestion.json` and a lean summary (pointers + counts, never blobs)
to `run_metadata.json`.

**Processors** (`backend/app/pipeline/processors/`) — each returns
`{"status": "success", "filename": ..., "metrics": {...}, ...}`:

- `text.py` — `process_text(str)`: strips zero-width chars + URLs, normalizes whitespace.
- `image.py` — `process_image(path, max_longest_edge=1024)`: validates format, RGBA/P→RGB,
  downscales, encodes to JPEG base64 data URI.
- `video.py` — `process_video(path, sidecar_url)`: delegates keyframe extraction to the ffmpeg
  sidecar, then runs each frame through `process_image`.
- `model.py` — `process_model(path, sidecar_url)`: delegates to the renderer sidecar, then runs
  each thumbnail through `process_image`. Accepts `.glb`/`.gltf`/`.obj`, or a `.zip` bundle of a
  multi-file glTF (extracted with zip-slip protection; the `.gltf`/`.glb` entrypoint is rendered).

Processors raise `FileNotFoundError` for missing files and `*ProcessingError` / `ValueError` for
invalid input.

**Other core modules:**

- `app/core/run_manager.py` — creates runs and moves staged uploads into `inputs/` as
  `{field}_{filename}` (the field prefix prevents collisions).
- `app/core/settings.py` — env-driven config (`FFMPEG_SIDECAR_URL`, `RENDERER_SIDECAR_URL`,
  `CONTENT_DIR`, API keys, CORS).
- `app/api/routes/` — `uploads.py` (`POST /api/uploads`), `runs.py` (`POST /api/runs/submit`),
  `sse.py` (run event stream).

## Renderer Sidecar Notes

Off-screen WebGL via **headless-gl** needs an X display: `entrypoint.sh` starts `Xvfb` then
`exec`s node as PID 1. glTF/GLB are loaded with **node-three-gltf** (handles external buffers +
textures and decodes images via `@napi-rs/canvas`, no DOM); OBJ uses Three's `OBJLoader`. The
Dockerfile uses `node:20-bookworm-slim` with mesa/build deps. A `.gltf` that references files not
present returns `422` telling the user to upload a self-contained `.glb` or a `.zip` of the folder.

## Running the Stack

```bash
cp .env.example .env   # fill in API keys
docker compose up --build
```

## Running Tests

Backend tests use **pytest** (asyncio auto-mode) and mock the sidecar HTTP calls — no running
containers needed. From `backend/`:

```bash
pip install -e ".[dev]"   # fastapi, langgraph, pytest, pytest-asyncio, ruff, ...
python -m pytest
```

Lint with `ruff check app tests`.

The legacy `testing/` scripts are run differently (from the repo root, no framework):

```bash
python -m testing.test_image
python -m testing.test_text
```

## Dependencies

- **Backend:** declared in `backend/pyproject.toml` (FastAPI, LangGraph, Pillow, httpx, …).
- **Renderer:** `services/renderer/package.json` (`three`, `gl`, `node-three-gltf`, `pngjs`,
  `express`); native deps build inside the Docker image.
- **Legacy `data_processing/`:** requires `Pillow` (`pip install Pillow`).
