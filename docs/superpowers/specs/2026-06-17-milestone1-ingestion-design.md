# Milestone 1 — Submission Form & Ingestion Endpoint Design

**Date:** 2026-06-17  
**Status:** Approved  
**Scope:** Next.js submission form + FastAPI ingestion endpoint (Milestone 1 of PRD v2.0)

---

## Overview

Implement the user-facing submission form and the backend ingestion API that receives, validates, and stores all pipeline inputs before handing off to the LangGraph pipeline.

---

## Frontend Form (`frontend/app/page.tsx`)

Replace the current "Start Run" stub with a functional accordion form. No visual polish — focus on correctness and wiring.

### Layout

Shadcn `Accordion` with five sections:

| # | Section | Default |
|---|---|---|
| 1 | Required Inputs | Open |
| 2 | Optional Media | Closed |
| 3 | Visual Steering | Closed |
| 4 | Pipeline Mode | Closed |
| 5 | Supervision | Closed |

### Section 1 — Required Inputs

- **Product Image** — file input (jpg/jpeg/png/webp). Uploads immediately on file selection via `POST /api/uploads?file_type=product_image`. Shows "uploading… / ready / error" inline text.
- **Product Info** — `<textarea>` (required)
- **Target Audience** — `<textarea>` (required)
- **Desired Colors** — `<textarea>` (required)

### Section 2 — Optional Media

Each file input uploads immediately on selection. All produce an `upload_token` stored in component state.

- **Product Video** — file input (mp4/mov/webm, max 100MB). `file_type=video`
- **3D Model** — file input (gltf/obj/usdz, max 50MB). `file_type=model_3d`
- **Reference Image** — file input (jpg/jpeg/png/webp, max 20MB). `file_type=reference_image`
- **Logo** — file input (svg/png/jpeg, max 10MB). `file_type=logo`
- **Logo Placement** — `<select>`: Top-Left / Top-Right / Bottom-Left (default) / Bottom-Right / Center Watermark. Enabled only when a logo token is present.

### Section 3 — Visual Steering

All dropdowns/selects with hardcoded option lists from PRD:

- **Aspect Ratio** — `1:1 Square` (default) / `9:16 Vertical` / `16:9 Landscape` / `4:5 Portrait`
- **Camera Perspective** — `Studio Eye-Level` (default) / `Flat Lay (Top-Down)` / `Close-Up Macro` / `Dynamic 3/4 View` / `Hero Shot (Low Angle)`
- **Lighting / Vibe Preset** — `Studio Softlight` (default) / `Natural Sunshine` / `Golden Hour Warmth` / `Moody / Chiaroscuro` / `Neon / Cyberpunk` / `Minimalist Pastel`
- **Negative Prompts** — `<textarea>` (optional, empty default)

### Section 4 — Pipeline Mode

Radio group or select for 5 modes:
- `summarize` — Summarization & Research Opt-In
- `ecommerce` — E-Commerce Batch (shows numeric input: 5–12 images)
- `social` — Social Media Marketing (shows research toggle)
- `ab` — A/B Concept Exploration (shows optional concept directions textarea)
- `seasonal` — Seasonal / Holiday Campaign (shows seasonal theme dropdown: Christmas / Halloween / Summer / Spring / Diwali / Black Friday / Valentine's Day / Eid / Hanukkah / New Year)

Default: `ecommerce`.

### Section 5 — Supervision

Two toggles (boolean, default ON):
- Research supervision
- Image generation supervision

Final Review Deck is always shown — no toggle.

### Submit Button

Disabled until: `product_image_token` is set AND all three description textareas are non-empty.

On click: POSTs JSON to `POST /api/runs/submit`. On success, stores `run_id` and transitions to existing SSE pipeline view.

---

## Backend API

### `POST /api/uploads`

**Query param:** `file_type` — one of `product_image`, `reference_image`, `logo`, `video`, `model_3d`

**Body:** `multipart/form-data` with a single `file` field.

**Validation:**

| file_type | Accepted MIME / extensions | Max size |
|---|---|---|
| product_image | jpg, jpeg, png, webp | 20MB |
| reference_image | jpg, jpeg, png, webp | 20MB |
| logo | svg, png, jpeg | 10MB |
| video | mp4, mov, webm | 100MB |
| model_3d | gltf, obj, usdz | 50MB |

Validation checks: extension + MIME type match expected types, file size within limit.

On success: saves file to `content/uploads/<upload_token>/<original_filename>`, returns:
```json
{ "upload_token": "<uuid4>" }
```

On failure: returns 422 with a clear error message.

**New route file:** `backend/app/api/routes/uploads.py`

---

### `POST /api/runs/submit`

**Body:** JSON

```json
{
  "description_product": "...",
  "description_audience": "...",
  "description_colors": "...",
  "product_image_token": "<uuid>",
  "video_token": "<uuid | null>",
  "model_3d_token": "<uuid | null>",
  "reference_image_token": "<uuid | null>",
  "logo_token": "<uuid | null>",
  "logo_placement": "bottom-left",
  "steering": {
    "aspect_ratio": "1:1",
    "camera_perspective": "Studio Eye-Level",
    "lighting_preset": "Studio Softlight",
    "negative_prompts": ""
  },
  "pipeline_mode": "ecommerce",
  "ecommerce_image_count": 5,
  "social_research_enabled": false,
  "ab_concept_directions": "",
  "seasonal_theme": null,
  "supervision": {
    "research": true,
    "image_gen": true
  }
}
```

**Validation:** All three description fields non-empty; `product_image_token` resolves to a file in `content/uploads/`; `pipeline_mode` is one of the 5 valid values; `ecommerce_image_count` between 5–12 if mode is `ecommerce`; `seasonal_theme` non-null if mode is `seasonal`.

**On success:**
1. Call `run_manager.create_run()` to get a `run_id` and create `content/<run_id>/inputs/`.
2. Move all resolved staged files from `content/uploads/<token>/` into `content/<run_id>/inputs/`.
3. Write `run_metadata.json` with all inputs, steering, mode, supervision, and `status: "running"`.
4. Return `{ "run_id": "<uuid>" }`.

Extend existing `backend/app/api/routes/runs.py` with the `/submit` route, or keep it in a new `runs_submit.py` — implementation decision deferred to plan.

---

## Data Flow

```
User selects file
  → POST /api/uploads?file_type=X
  → file saved to content/uploads/<token>/
  → upload_token returned, stored in React state

User clicks Submit
  → POST /api/runs/submit (JSON: text fields + tokens)
  → backend validates + resolves tokens
  → files moved to content/<run_id>/inputs/
  → run_metadata.json written
  → run_id returned
  → frontend transitions to SSE pipeline view
```

---

## Files Touched

**Frontend:**
- `frontend/app/page.tsx` — replace stub with accordion form

**Backend:**
- `backend/app/api/routes/uploads.py` — new file, upload endpoint
- `backend/app/api/routes/runs.py` — add `/submit` route
- `backend/app/core/run_manager.py` — extend to accept and write full metadata on run creation
- `backend/app/main.py` — register uploads router

**Shadcn components needed** (add if not present):
- `accordion`
- `label`
- `textarea`
- `select`
- `switch` (for supervision toggles)
- `input`

---

## Out of Scope

- FFmpeg keyframe extraction (Milestone 1 stores the video file only)
- Three.js 3D rendering (Milestone 1 stores the model file only)
- LangGraph pipeline execution (run is created but pipeline invocation is not wired in this milestone)
- Frontend visual polish, loading skeletons, animations
