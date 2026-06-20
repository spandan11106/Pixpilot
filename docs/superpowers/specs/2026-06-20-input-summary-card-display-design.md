# Input Summary Card Display — Design Spec

**Date:** 2026-06-20  
**Status:** Approved

## Problem

The backend `summary_agent_node` generates an Input Summary Card (product name, category, features, audience, colors, materials, style vibe) and stores it in `run_metadata.json`. The live event log in `RunView` shows `summary_complete` as a plain log row — the card data is never surfaced to the user.

## Approach

Extend the `summary_complete` SSE event payload to include the full summary card dict, then render it as a structured inline card in the live event log at the position where the event fires.

No new endpoints, no extra HTTP fetches, no new components.

## Backend Change

**File:** `backend/app/pipeline/graph.py` — `summary_agent_node`

Add `summary_card` to the `summary_complete` event payload:

```python
return _emit(
    state,
    "summary_complete",
    {
        "vision_available": summary_card.get("vision_available", False),
        "product_name": summary_card.get("product_name"),
        "summary_card": summary_card,   # ← add this
    },
    results=results,
)
```

The full card is ~200 bytes of JSON and fits comfortably in the SSE frame.

## Frontend Change

**File:** `frontend/components/dashboard/RunView.tsx`

In the log row renderer, detect `msg.event === "summary_complete"` and render a card block instead of a plain row. The card reads `msg.data.summary_card` (typed as `Record<string, unknown>` via the existing `SSEMessage.data` field).

### Card layout (inline in the log scroll area)

```
┌─ Input Summary Card ──────────────────────────────────────────┐
│ product_name           product_category                       │
│                                                               │
│ Key Features   • feature 1  • feature 2  • feature 3         │
│ Audience       description of the target audience             │
│ Colors         ● #hex1   ● #hex2   ● #hex3                    │
│ Materials      material 1   material 2                        │
│ Style Vibe     overall aesthetic vibe                         │
│ Vision         ✓ Available  /  ✗ Text-only                    │
└───────────────────────────────────────────────────────────────┘
```

Styling: slightly more padding than a plain log row, left accent border (using existing CSS variable for success/accent color), title row with `overline` typography. All other log rows render unchanged.

### Fields rendered

| Field | Source key | Render |
|---|---|---|
| Product name | `product_name` | Bold heading |
| Category | `product_category` | Muted subheading |
| Key features | `key_features` | Bullet list |
| Target audience | `target_audience` | Text row |
| Dominant colors | `dominant_colors` | Color swatch + hex |
| Materials | `materials` | Tag list |
| Style vibe | `style_vibe` | Highlighted label |
| Vision available | `vision_available` | Badge (✓/✗) |

## Error / Fallback

If `summary_card` is absent from the event data (e.g. older backend), the row falls back to the existing plain log row format — no crash.

## Out of Scope

- Creative blueprint / image prompt display (separate future feature)
- Editing or re-generating the summary card from the UI
- Displaying the card in the Generations history page
