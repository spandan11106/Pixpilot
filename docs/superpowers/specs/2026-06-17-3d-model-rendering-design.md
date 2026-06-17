# 3D Model Rendering via Three.js Sidecar — Design

**Date:** 2026-06-17
**Status:** Implemented (2026-06-18)

## Purpose

When a run includes a 3D model, the pipeline takes snapshots of the model from
several perspectives and feeds those thumbnails to the image generation model as
additional product context. This replaces the Milestone 0 stub renderer with a
real headless Three.js implementation that produces 4 perspective thumbnails.

## Decisions

- **Render engine:** headless-gl (`gl` npm package) + Three.js, off-screen WebGL.
  No browser. A virtual X display (Xvfb) is required for the Mesa GL context.
- **Model loading:** `node-three-gltf` for `.gltf`/`.glb` (it loads external
  buffers/textures from disk and decodes images via `@napi-rs/canvas`, with no
  DOM); Three's `OBJLoader` for `.obj`.
- **Accepted formats:** `.glb` and `.gltf` (incl. multi-file bundles via `.zip`),
  plus `.obj`. A multi-file `.gltf` cannot survive a single-file upload (its
  external `.bin`/textures are lost), so users upload either a self-contained
  `.glb` or a `.zip` of the whole glTF folder. USDZ remains accepted at upload but
  is rejected by the renderer and surfaces as a non-fatal `model_failed`.
- **Angles:** front, three-quarter (hero), side, back — orbit at eye-level with the
  hero view angled slightly up. Top-down dropped as least informative for products.
- **Framing:** each view is framed by a tight per-view bounding-box fit (project
  the 8 box corners into the frustum, move as close as possible while keeping every
  corner in frame), with a small padding margin so the product nearly fills the
  thumbnail while remaining wholly visible.
- **Optionality:** the 3D model is optional and non-fatal, exactly like video.

## Architecture

The 3D path mirrors the existing video path: a backend processor delegates the
heavy work to a Docker sidecar, then reuses `process_image` to turn the sidecar's
output files into base64 data URIs.

```
process_video → process_model → finalize
```

The renderer and backend share the same `content/` mount, so a `.zip` extracted by
the backend is visible to the sidecar at the same path.

### 1. Renderer sidecar (`services/renderer/`)

Real Three.js renderer behind `POST /render-3d`.

**Contract:**

- Request: `{ "model_path": string, "output_dir"?: string }`
- Response `200`: `{ "thumbnails": string[], "metrics": { ... } }` — 4 PNG paths
- Response `400`: unsupported format
- Response `404`: missing file
- Response `422`: render failure (incl. a glTF referencing files that were not
  uploaded — the error tells the user to upload a `.glb` or a `.zip` of the folder)

**Rendering flow:**

1. Resolve format from the file extension.
   - `.gltf` / `.glb` → `node-three-gltf` `loadGltf`
   - `.obj` → `OBJLoader` (normals computed + a default material applied so it is
     visible under lighting)
   - anything else (incl. `.usdz`) → `400 { error: "unsupported format: <ext>" }`
2. Compute the bounding box and its 8 corners.
3. Lighting: low ambient + a key and a fill directional light from different
   angles, so faces read at distinct brightnesses and edges stay legible.
   Background: solid white.
4. For each of the 4 views, compute the orbit direction, then the smallest camera
   distance that keeps every box corner in frame (`fitDistance`), apply the framing
   margin, position the camera, and render at 1024×1024 (PNG).
   - `front` — straight on
   - `three_quarter` — ~45° azimuth, angled slightly up (hero)
   - `side` — 90° azimuth
   - `back` — 180° azimuth
5. Output directory defaults to `<model_dir>/renders`. Clear any stale renders
   first, then write the 4 PNGs.
6. Return the 4 paths plus metrics: vertex count, face count, bounding box dims.

**Dependencies:** `three`, `gl`, `node-three-gltf`, `pngjs`, `express`.

**Dockerfile / startup:** `node:20-bookworm-slim` with `gl`'s build/runtime deps
(`python3`, `make`, `g++`, `pkg-config`, `libgl1-mesa-dev`, `libxi-dev`,
`libglu1-mesa-dev`, `libglew-dev`) plus `xvfb` and `xauth`. An `entrypoint.sh`
starts `Xvfb` on `:99` and then `exec`s node as PID 1 (running `xvfb-run` as PID 1
proved unreliable).

### 2. Backend processor (`backend/app/pipeline/processors/model.py`)

`process_model(file_path, sidecar_url, *, delete_raw=True)`, mirroring
`process_video`:

- Raise `FileNotFoundError` if the model file is missing.
- If the file is a `.zip`: extract it with zip-slip protection, resolve the
  shallowest `.gltf`/`.glb` entrypoint, and render that. No entrypoint → raise
  `ModelProcessingError`.
- POST the resolved path to `<sidecar_url>/render-3d`.
- On unreachable sidecar, non-200 response, or empty thumbnail list → raise
  `ModelProcessingError`.
- Run each returned PNG through `process_image` to produce base64 data URIs.
- On success with `delete_raw`, delete the raw model (and the extraction dir for a
  zip); models can be up to 50MB and only the thumbnails are needed downstream.
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

### 3. Upload validator (`backend/app/api/routes/uploads.py`)

`model_3d` accepts `gltf`, `glb`, `obj`, `usdz`, `zip` (50MB).

### 4. Pipeline graph (`backend/app/pipeline/graph.py`)

Async `process_model_node` between `process_video` and `finalize`:

- Read `model_3d_path` from run inputs. Absent → `model_skipped` and continue.
- Call `process_model(...)` with `settings.renderer_sidecar_url`.
- On any exception → `model_failed` (`{"error": str(e)}`), continue (non-fatal).
- On success → store under `results["model_3d"]`, emit `model_processed`.

`finalize_node` summary gains `model_3d_thumbnail_count`.

### 5. Tests (`backend/tests/`)

Mock the sidecar HTTP call (no real renderer needed):

- `process_model`: missing file → `FileNotFoundError`; non-200 / unreachable /
  empty thumbnails → `ModelProcessingError`; success → 4 thumbnails + raw deleted.
- Zip handling: bundle with `.gltf`+`.bin` resolves and renders the entrypoint and
  cleans up; bundle with no entrypoint raises; zip-slip member rejected.
- Uploads: `.glb` and `.zip` accepted; unsupported extension rejected.
- Pipeline: no model → `model_skipped`; failure → `model_failed` (run still
  completes); success → `model_processed`, `ingestion.json` has `model_3d` with 4
  thumbnails, finalize summary reports `model_3d_thumbnail_count == 4`.

## Implementation Notes (deltas found during build)

These were discovered while getting the sidecar running in Docker:

- `xvfb-run` needs `xauth`, and as PID 1 it died silently — replaced with an
  `entrypoint.sh` that starts `Xvfb` and `exec`s node.
- Three's `WebGLRenderer.dispose()` reads `cancelAnimationFrame` off the global
  `self`, absent in Node — added `self` + no-op `requestAnimationFrame`/
  `cancelAnimationFrame` globals.
- The browser `GLTFLoader` cannot load external `.bin`/textures in Node (it fetches
  bare filesystem paths); `node-three-gltf` replaces it and handles disk resources
  + image decoding.
- Bounding-sphere framing looked far away; switched to the tight per-view
  bounding-box fit described above.

## Out of Scope

- USDZ rendering (handled as an unsupported skip).
- Animation / turntable GIFs.
- Configurable angle sets or per-run camera control.
- Frontend changes — the 3D upload field already exists (a UI hint to prefer
  `.glb`/`.zip` would be a nice future addition).
