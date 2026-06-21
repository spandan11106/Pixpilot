# Image Designer Agent — Design Spec
**Date:** 2026-06-21
**Status:** Approved
**Milestone:** 2 — Image Generation with Preview & Revision Loop

---

## Overview

This spec covers the full Milestone 2 implementation: an Image Designer Agent that builds a
FLUX prompt from the existing `creative_blueprint`, calls the fal.ai FLUX Dev image-to-image
endpoint with async queue polling, streams SSE events during generation, and supports a
user-driven revision loop (up to 10 iterations) via a dedicated HTTP endpoint. Logo compositing
is deferred to a later milestone.

---

## Architecture

### New files

```
backend/app/pipeline/agents/image_designer.py   — FLUX prompt builder + fal.ai async client
backend/app/api/routes/revise.py                — POST /api/runs/{run_id}/revise
                                                  GET  /api/runs/{run_id}/images/{filename}
frontend/components/dashboard/ImageWorkspace.tsx — inline image preview + revision form
```

### Modified files

```
backend/app/pipeline/graph.py       — add image_designer node after summary_agent
backend/app/core/settings.py        — add fal_image_model setting
backend/app/api/routes/__init__.py  — register revise router
backend/app/main.py                 — mount revise router
backend/pyproject.toml              — add fal-client dependency
frontend/…SupervisionPanel or SSE event log component
                                    — detect image_generation_complete, render ImageWorkspace
```

### Updated pipeline graph

```
start → process_text → process_image → process_reference → process_video
      → process_model → finalize → vision_analysis → summary_agent
      → image_designer → complete
```

`image_designer` is **fatal on failure** (same policy as `process_image`): if FLUX fails after
retries the run is marked failed and the graph routes to END.

Exception: if `creative_blueprint` is absent (summary agent failed), the node emits
`image_generation_skipped`, leaves `state["failed"]` as `False`, and routes to `complete`
(non-fatal — the earlier failure is already logged).

---

## Backend: Image Designer Agent

### File: `backend/app/pipeline/agents/image_designer.py`

#### Prompt builder

Assembles the `creative_blueprint` dict into a single FLUX prompt string. No LLM call — the
Summary Agent already produced all fields.

```
{subject}. {style}. {lighting}. {background}. {composition}. {color_palette}.
Camera: {camera_angle}. Lighting preset: {lighting_preset}.
Negative: {negative_prompts}.
```

#### fal.ai async client

```python
async def generate_image(
    prompt: str,
    image_data_uri: str,   # base64 data URI from ingestion results
    aspect_ratio: str,
    negative_prompts: str,
    seed: int | None = None,
) -> dict:
    # 1. Upload product image to fal storage → cdn_url
    # 2. fal_client.submit("fal-ai/flux/dev/image-to-image", arguments={...}) → request_id
    # 3. Poll fal_client.status(request_id) every 3 s
    # 4. On COMPLETED → fetch result → return {image_url, seed, latency_ms}
    # 5. On ERROR → raise ImageGenerationError
    # 2 retries (fresh submit each time) before propagating
```

`fal_client` is configured with `FAL_KEY` from settings at module import time.

#### LangGraph node

```python
async def image_designer_node(state: PipelineState) -> dict:
```

- Reads `creative_blueprint` from `state["results"]`; if absent emits `image_generation_skipped`
- Reads `state["results"]["image"]["image_payload"]` (base64 data URI)
- Emits `image_generation_started` SSE event
- Calls `generate_image()` with async polling
- On success:
  - Downloads image bytes from the fal CDN URL
  - Saves to `content/<run_id>/v1.png`
  - Emits `image_generation_complete` with `{image_path, image_url, seed, prompt_used, iteration: 1}`
  - Appends to `run_metadata.json` under `image_iterations`
  - Updates `run_metadata.json` `status` → `"image_generated"`
- On failure (after retries):
  - Emits `image_generation_failed` with `{error, retries: 2}`
  - Sets `state["failed"] = True`, marks run `status` → `"failed"`
  - Routes to END

#### Settings addition

```python
fal_image_model: str = "fal-ai/flux/dev/image-to-image"
```

---

## Backend: Revision Endpoint

### File: `backend/app/api/routes/revise.py`

#### `POST /api/runs/{run_id}/revise`

**Request body:**
```json
{ "feedback": "Make the background darker and add golden lighting", "iteration": 1 }
```

**Steps:**
1. Validate `iteration < 10`; if not, return `400 {"error": "max_iterations_reached"}`
2. Load last prompt from `run_metadata.json` `image_iterations[-1].prompt`
3. Load product profile from `run_metadata.json` `agent_states.product_profile` (for
   product-preservation tokens)
4. Load product image data URI from `content/<run_id>/processed/ingestion.json`
   (`results.image.image_payload`) — same base image used for every revision iteration
5. Call Refinement Agent (Claude Sonnet, single call) → revised prompt string
6. Call `generate_image()` with revised prompt and original product image
6. Save output to `content/<run_id>/v{iteration+1}.png`
7. Append to `image_iterations` in `run_metadata.json`
8. Return `{iteration, image_path, image_url: "/api/runs/{run_id}/images/v{n}.png" (resolved), prompt_used, seed}`

**On Refinement Agent failure:** return `500 {"error": "..."}` — frontend shows error, user
retries same iteration (counter not incremented).

**On FLUX failure (after 2 retries):** return `500` — same recovery path.

#### Refinement Agent

Single Claude Sonnet call. System prompt instructs it to:
- Rewrite the generation prompt incorporating the user feedback
- Remove tokens that contradict the requested change
- Preserve product-description tokens (shape, label, geometry)

Returns a plain prompt string (not JSON).

#### `GET /api/runs/{run_id}/images/{filename}`

Serves `content/<run_id>/{filename}` as a static binary response.
Returns `404` if file does not exist. Only `.png` and `.jpg` extensions accepted (rejects path
traversal attempts via filename validation).

---

## Frontend: ImageWorkspace

### File: `frontend/components/dashboard/ImageWorkspace.tsx`

Rendered **inline** in the existing event log after the `image_generation_complete` SSE event.
No routing change, no new views.

**Component state:**
- `imageSrc` — `/api/runs/{run_id}/images/v1.png` (updated after each revision)
- `iteration` — current iteration (starts at 1)
- `feedback` — controlled text input value
- `status: "idle" | "submitting" | "error"`
- `approved` — boolean

**Layout:**
```
┌──────────────────────────────────────────┐
│  [Generated Image — full width preview]  │
│                                          │
│  Iteration 1 of 10                       │
│                                          │
│  What would you like to change?          │
│  [text input ..........................]  │
│                                          │
│  [Submit Revision]  [Approve & Download] │
└──────────────────────────────────────────┘
```

**Submit Revision:** POST to `/api/runs/{run_id}/revise`, disable inputs, show spinner. On
response: update `imageSrc`, increment `iteration`, clear `feedback`.

**Approve & Download:** Fetches current image, triggers browser download as
`pixpilot_v{iteration}.png`. Replaces revision form with "Run complete" message.

**Max iterations reached:** Revision form replaced with "Maximum revisions reached — approve
the current image or start a new run."

**Error:** Inline error message below the form; form re-enabled.

---

## Data Structures

### `image_iterations` in `run_metadata.json`

```json
"image_iterations": [
  {
    "iteration": 1,
    "prompt": "Luxury skincare serum bottle...",
    "seed": 42,
    "output_path": "v1.png",
    "feedback": null
  },
  {
    "iteration": 2,
    "prompt": "Luxury skincare serum bottle... darker background...",
    "seed": 87,
    "output_path": "v2.png",
    "feedback": "Make the background darker and add golden lighting"
  }
]
```

### `image_generation_complete` SSE event payload

```json
{
  "event": "image_generation_complete",
  "data": {
    "iteration": 1,
    "image_path": "v1.png",
    "image_url": "/api/runs/{run_id}/images/v1.png",
    "prompt_used": "...",
    "seed": 42
  }
}
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| `FAL_KEY` missing | `image_generation_failed` SSE immediately; run → failed |
| FLUX job error after 2 retries (initial) | `image_generation_failed` SSE; run → failed |
| fal upload fails (product image) | Fatal — same as above |
| `creative_blueprint` absent | `image_generation_skipped` SSE; routes to `complete` |
| Refinement Agent fails | `/revise` → 500; frontend shows error; user retries |
| FLUX fails during revision after 2 retries | `/revise` → 500; iteration not incremented |
| Image file write fails | Fatal; run → failed |
| `iteration >= 10` | `/revise` → 400 `max_iterations_reached` |
| Invalid filename in image serve route | 400 rejected before disk access |

---

## Testing

| Test file | Coverage |
|---|---|
| `tests/test_image_designer.py` | Prompt builder (pure), mock fal client (submit/poll/complete + error + retry) |
| `tests/test_revise.py` | `/revise` endpoint: mock Anthropic + mock fal; max-iteration guard; 500 paths |
| `tests/test_image_serving.py` | Image serve route: 200 with correct bytes, 404, path-traversal rejection |
| `tests/test_pipeline.py` (extended) | `image_designer` node emits correct SSE events; failure routes to END |

All fal.ai calls are mocked — no live network calls in tests.

---

## Dependencies

- `fal-client` — add to `backend/pyproject.toml`
- `httpx` (already present) — used for downloading generated image from fal CDN URL
