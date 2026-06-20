# Plan: Models & API Keys Settings Page

## Context

The sidebar already has a "Models" nav item but it's disabled (no-op). This plan wires it to a new settings page where users can manage API keys for each AI provider, set model names, and drag-and-drop the fallback priority order for the Vision agent. The backend currently reads all config from `.env` at startup with no runtime-editable endpoint — this plan adds one.

---

## Approach

### 1. Backend — `GET /api/settings` + `PATCH /api/settings`

**New file:** `backend/app/api/routes/settings.py`

- `GET /api/settings` — reads current values from the live `Settings` object and returns them. API keys are masked: show only first 4 + last 4 chars (e.g., `sk-p...abcd`), or empty string if unset.
- `PATCH /api/settings` — accepts a partial body, writes changed values to `.env` using `python-dotenv`'s `set_key()`, then reloads the `Settings` singleton so the running process picks up the new values immediately (no restart needed).

Fields covered:

| Setting | JSON key |
|---|---|
| `OPENAI_API_KEY` | `openai_api_key` |
| `ANTHROPIC_API_KEY` | `anthropic_api_key` |
| `GOOGLE_API_KEY` | `google_api_key` |
| `FAL_API_KEY` | `fal_api_key` |
| `SERPAPI_API_KEY` | `serpapi_api_key` |
| `OPENAI_VISION_MODEL` | `openai_vision_model` |
| `ANTHROPIC_VISION_MODEL` | `anthropic_vision_model` |
| `GOOGLE_VISION_MODEL` | `google_vision_model` |
| `SUMMARY_MODEL` | `summary_model` |
| `PROMPT_MODEL` | `prompt_model` |
| `VISION_MODELS` (priority order) | `vision_priority` (comma-joined list, e.g. `"openai,anthropic,google"`) |

**Register in** `backend/app/main.py` — add `from app.api.routes import settings` and `app.include_router(settings.router, prefix="/api")`.

**Dependency:** `python-dotenv` is likely already available (pydantic-settings uses it); verify in `backend/pyproject.toml`. Add if missing.

---

### 2. Frontend — `AppView` type + Sidebar

**File:** `frontend/components/dashboard/Sidebar.tsx`

- Add `"models"` to `AppView` type: `export type AppView = "workflow" | "generations" | "models";`
- Remove the `disabled` attribute from the Models button and wire `onClick` to `onViewChange("models")`.

---

### 3. Frontend — Dashboard routing

**File:** `frontend/components/dashboard/Dashboard.tsx`

Add a branch to the render logic:

```tsx
{view === "models" ? (
  <ModelsPage />
) : view === "generations" ? (
  <GenerationsPage />
) : activeRun ? (
  <RunView ... />
) : (
  <EmptyState ... />
)}
```

Import `ModelsPage` from `./ModelsPage`.

---

### 4. Frontend — `ModelsPage` component

**New file:** `frontend/components/dashboard/ModelsPage.tsx`

**On mount:** `GET /api/settings` — populate local state with masked key display values and model names.

**Layout (two-column card grid, same visual style as the rest of the dashboard):**

#### Section A — API Keys
One card per provider (OpenAI, Anthropic, Google, Fal, SerpAPI). Each card has:
- Provider name + icon/label
- Password input for the key (shows masked value from server; typing replaces it)
- A "saved" indicator that clears on edit

#### Section B — Models
One card per model role:
- Vision → OpenAI model name
- Vision → Anthropic model name
- Vision → Google model name
- Summary model (Anthropic)
- Prompt model (Anthropic)

#### Section C — Vision Priority (drag-and-drop)
Three draggable cards: OpenAI · Anthropic · Google. Their vertical order maps to `vision_priority`. Use **`@dnd-kit/core` + `@dnd-kit/sortable`** (install via `npm install @dnd-kit/core @dnd-kit/sortable` in `frontend/`). A drag handle icon on each card enables reordering.

**Save button:** collects all state and sends `PATCH /api/settings`. Shows a success toast / error message.

---

### 5. Install DnD dependency

```bash
cd frontend && npm install @dnd-kit/core @dnd-kit/sortable
```

---

## Files to Create / Modify

| Action | File |
|---|---|
| Create | `backend/app/api/routes/settings.py` |
| Modify | `backend/app/main.py` — register settings router |
| Modify | `frontend/components/dashboard/Sidebar.tsx` — add "models" to type, enable button |
| Modify | `frontend/components/dashboard/Dashboard.tsx` — add models branch |
| Create | `frontend/components/dashboard/ModelsPage.tsx` |

---

## Verification

1. `docker compose up` (or `uvicorn` dev server) — confirm `GET /api/settings` returns masked keys and current model values.
2. Navigate to Models tab in the sidebar — page renders without errors.
3. Change an API key and click Save — `PATCH /api/settings` returns 200 and the `.env` file is updated on disk.
4. Restart backend — new key value is loaded (confirming `.env` write persisted).
5. Drag Vision providers into a new order and Save — `GET /api/settings` returns the updated `vision_priority` string.
6. Run backend tests: `cd backend && python -m pytest` — no regressions.
