# 3D Model Rendering via Three.js Sidecar — Design

**Date:** 2026-06-17
**Status:** Approved

## Purpose

When a run includes a 3D model (`gltf`/`glb`/`obj`), the pipeline takes snapshots
of the model from several perspectives and feeds those thumbnails to the image
generation model as additional product context. This replaces the Milestone 0
stub renderer with a real headless Three.js implementation that produces 4
perspective thumbnails.

## Decisions

- **Render engine:** headless-gl (`gl` npm package) + Three.js, off-screen WebGL.
  No browser.
- **Formats:** GLTF/GLB + OBJ only. USDZ (and any other extension) is rejected by
  the renderer and handled as a non-fatal skip. The upload validator continues to
  accept `usdz` so the upload itself does not block; the unsupported model surfaces
  as a `model_failed` event later.
- **Angles:** front, three-quarter (hero), side, back — auto-framed, eye-level
  orbit with the hero view angled slightly up. Top-down dropped as least
  informative for products.
- **Optionality:** the 3D model is optional and non-fatal, exactly like video.

## Architecture

The 3D path mirrors the existing video path: a backend processor delegates the
heavy work to a Docker sidecar, then reuses `process_image` to turn the sidecar's
output files into base64 data URIs.

```
process_video → process_model → finalize
```

### 1. Renderer sidecar (`services/renderer/`)

Replace the stub `POST /render-3d` with a real Three.js renderer.

**Contract (unchanged shape):**

- Request: `{ "model_path": string, "output_dir"?: string }`
- Response `200`: `{ "thumbnails": string[], "metrics": { ... } }` — 4 PNG paths
- Response `400`: `{ "error": string }` for unsupported format
- Response `404`: `{ "error": string }` for missing file

**Rendering flow:**

1. Resolve format from the file extension.
   - `.gltf` / `.glb` → `GLTFLoader`
   - `.obj` → `OBJLoader`
   - anything else (incl. `.usdz`) → `400 { error: "unsupported format: <ext>" }`
2. Load the model into a scene. Compute the bounding box; auto-frame by placing
   the camera at a distance that fits the box, targeting the box center.
3. Lighting: ambient + a key directional light. Background: solid white (clean
   product-shot context for the downstream image-gen model).
4. Render 4 views at 1024×1024 (PNG), orbiting at eye-level elevation:
   - `front` — straight on
   - `three_quarter` — ~45° azimuth, angled slightly up (hero)
   - `side` — 90° azimuth
   - `back` — 180° azimuth
5. Output directory defaults to `<model_dir>/renders`. Clear any stale renders
   first (mirrors the ffmpeg sidecar's frame cleanup), then write the 4 PNGs.
6. Return the 4 paths plus metrics: vertex count, face count, bounding box dims.

**Dependencies:** add `three` and `gl` to `package.json`.

**Dockerfile:** switch from `node:20-alpine` to `node:20-bookworm-slim` and install
the build/runtime deps that `gl` needs: `libgl1-mesa-dev`, `libxi-dev`, `python3`,
`g++`, `make` (and `xvfb`/mesa runtime libs as required for an off-screen context).

### 2. Backend processor (`backend/app/pipeline/processors/model.py`)

New `process_model(file_path, sidecar_url, *, delete_raw=True)`, mirroring
`process_video`:

- Raise `FileNotFoundError` if the model file is missing.
- POST to `<sidecar_url>/render-3d`.
- On unreachable sidecar, non-200 response, or empty thumbnail list → raise
  `ModelProcessingError`.
- Run each returned PNG through `process_image` to produce base64 data URIs.
- Delete the raw model after a successful render when `delete_raw` is true
  (models can be up to 50MB; the thumbnails are all the pipeline needs).
- Return:

```python
{
  "status": "success",
  "filename": <model file name>,
  "metrics": {
    "thumbnail_count": 4,
    "raw_model_deleted": <bool>,
    # plus sidecar metrics (vertex/face count, bbox dims)
  },
  "thumbnails": [ <process_image result>, ... ],
}
```

Export `process_model` from `app/pipeline/processors/__init__.py`.

### 3. Pipeline graph (`backend/app/pipeline/graph.py`)

Add an async `process_model_node` between `process_video` and `finalize`:

- Read `model_3d_path` from run inputs. Absent → emit `model_skipped`
  (`{"reason": "no 3D model provided"}`) and continue.
- Call `process_model(...)` with `settings.renderer_sidecar_url`.
- On any exception → emit `model_failed` (`{"error": str(e)}`) and continue
  (non-fatal, like video).
- On success → store under `results["model_3d"]` and emit `model_processed`
  (`{"thumbnail_count": ...}`).

Edges: `process_video → process_model → finalize`.

`finalize_node` summary gains:

```python
"model_3d_thumbnail_count": results.get("model_3d", {})
    .get("metrics", {}).get("thumbnail_count", 0),
```

### 4. Tests (`backend/tests/`)

Follow the existing `test_processors.py` / `test_pipeline.py` style (mock the
sidecar HTTP call; no real renderer needed):

- `process_model` raises `FileNotFoundError` for a missing file.
- `process_model` raises `ModelProcessingError` on sidecar non-200 / unreachable.
- `process_model` success path returns 4 thumbnails and deletes the raw model.
- Pipeline: no model → `model_skipped`, run completes.
- Pipeline: sidecar failure / unsupported format → `model_failed`, run still
  completes (non-fatal).
- Pipeline: success → `model_processed`, `ingestion.json` contains `model_3d` with
  4 thumbnails, and the finalize summary reports `model_3d_thumbnail_count == 4`.

## Out of Scope

- USDZ rendering (handled as an unsupported skip).
- Animation / turntable GIFs.
- Configurable angle sets or per-run camera control.
- Frontend changes — the 3D upload field already exists.
