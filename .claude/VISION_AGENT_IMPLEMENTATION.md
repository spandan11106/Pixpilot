# Vision Agent Implementation Guide

## Overview

The Vision Agent analyzes product media (image, video frames, 3D renders, reference image) and produces a structured `product_profile` JSON. It uses a **model-flexible provider architecture** that supports three vision models with automatic fallback:

1. **OpenAI GPT-4o Vision** (primary)
2. **Anthropic Claude 3.5 Sonnet** (fallback)
3. **Google Gemini 2.0 Vision** (fallback)

## Architecture

### Provider Pattern

Each vision model is wrapped in a **provider** that implements a consistent interface:

```
VisionProvider (Protocol)
  ├─ OpenAIVisionProvider
  ├─ AnthropicVisionProvider
  └─ GoogleVisionProvider
```

All providers implement:
```python
async def analyze(
    product_image: str,                    # base64 data URI (required)
    reference_image: str | None = None,    # base64 data URI (optional)
    video_frames: list[str] | None = None, # list of base64 data URIs (optional)
    model_thumbnails: list[str] | None = None,  # list of base64 data URIs (optional)
) -> dict[str, Any]
```

### Fallback Orchestrator

The `VisionOrchestrator` manages the fallback chain:

1. Reads `VISION_MODELS` from `.env` (e.g., `openai,anthropic,google`)
2. Filters to only available providers (those with API keys)
3. Tries each provider in order until one succeeds
4. Returns `None` if all providers fail (triggers human-in-the-loop checkpoint)

```python
orchestrator = VisionOrchestrator()
profile = await orchestrator.analyze(product_image, reference_image, ...)
```

## Configuration

### .env Setup

```env
# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Vision model fallback chain (tries in order)
VISION_MODELS=openai,anthropic,google
```

**Notes:**
- Only configure API keys for models you want to support
- The orchestrator will only try providers with valid API keys
- Reorder `VISION_MODELS` to change priority
- At least one model must be configured for the pipeline to proceed

## Integration with LangGraph Pipeline

### Pipeline Flow

```
start → process_text → process_image → process_reference 
→ process_video → process_model → finalize → [NEW] vision_analysis 
→ complete → END
```

The `vision_analysis` node is added after `finalize` and:

1. **Extracts base64 payloads** from the ingestion results
2. **Calls the orchestrator** to analyze media
3. **Handles failures** with a human-in-the-loop checkpoint:
   - If all providers fail → emit `vision_analysis_failed` event
   - User dashboard shows: "Vision analysis failed. Retry or skip?"
   - User selects: Skip (continue without vision analysis) or Retry
4. **Stores result** in `run_metadata.json` under `agent_states.product_profile`

### SSE Events

The vision analysis node emits SSE events to keep the frontend updated:

- `vision_analyzed` — Success
  ```json
  {"event": "vision_analyzed", "data": {"provider": "openai", "completeness": 0.9}}
  ```

- `vision_analysis_failed` — All providers failed, awaiting user action
  ```json
  {"event": "vision_analysis_failed", "data": {"reason": "All vision providers failed", "action_required": "User must choose to skip or retry"}}
  ```

- `vision_analysis_skipped` — No product image available
  ```json
  {"event": "vision_analysis_skipped", "data": {"reason": "No product image processed"}}
  ```

## Product Profile Schema

The Vision Agent returns a flexible dict that can vary by provider. All providers populate these core fields:

```python
product_profile = {
    # Core fields (all providers)
    "product_category": str,          # e.g., "cosmetic bottle"
    "dominant_colors": list[str],     # e.g., ["#F5E6D3", "#C8A882"]
    "materials_textures": list[str],  # e.g., ["amber glass", "plastic"]
    "usps": list[str],                # unique selling points
    "product_shape": str,             # e.g., "cylinder", "rectangular"
    
    # Optional fields (if reference/video/3D provided)
    "inferred_style_from_reference": dict | None,
    "lighting_conditions": str | None,
    "surface_finish": str | None,
    "scale_proportion": str | None,
    
    # Metadata
    "provider_used": str,             # "openai", "anthropic", or "google"
    "analysis_completeness": float,   # 0.0–1.0 (how much media was analyzed)
}
```

**Completeness Score:**
- 0.30 for product image (required)
- +0.20 if reference image present
- +0.25 if video frames present
- +0.25 if 3D model thumbnails present
- **Maximum: 1.0**

## Error Handling

### Graceful Degradation

The vision analysis is **non-fatal**:

- Missing or failed vision analysis does not halt the pipeline
- Emit `vision_analysis_skipped` and continue
- The Summary Agent and Image Gen Prompt Agent work with text description alone (lower quality)

### Provider Failures

When a provider fails (API error, timeout, invalid response):

1. Log the error with provider name
2. Try the next provider in the fallback chain
3. If all fail → emit checkpoint event
4. User decides: skip vision analysis or retry

## Testing

### Unit Tests

Tests are in `backend/tests/test_vision_agent.py`:

```bash
pytest tests/test_vision_agent.py -v
```

Coverage includes:
- Provider initialization
- JSON response parsing
- Fallback logic
- Orchestrator behavior

### Integration Testing

The vision analysis is tested end-to-end as part of the full pipeline:

```bash
# Coming in Milestone 2: Full E2E test with real product image
```

## File Structure

```
backend/
├── app/
│   ├── core/
│   │   └── settings.py            # Added google_api_key, vision_models
│   └── pipeline/
│       ├── graph.py               # Added vision_analysis_node
│       └── agents/
│           ├── vision_provider.py # Provider interface
│           ├── vision_orchestrator.py  # Orchestrator
│           └── providers/
│               ├── openai_provider.py
│               ├── anthropic_provider.py
│               └── google_provider.py
├── tests/
│   └── test_vision_agent.py       # Vision agent tests
└── pyproject.toml                 # Added openai, anthropic, google-generativeai
```

## Next Steps

1. **Summarizer Agent** — Merges `product_profile` + user description into Input Summary Card
2. **Image Gen Prompt Agent** — Generates creative blueprint from product profile + steering params
3. **Front-end Integration** — Display Input Summary Card + checkpoint UI for vision failures

## Cost Considerations

Vision model API costs per request:

| Model | Estimated Cost | Notes |
|-------|----------------|-------|
| GPT-4o Vision | ~$0.08–$0.12 | Depends on input size, token usage |
| Claude 3.5 Sonnet | ~$0.03–$0.06 | Multimodal, competitive pricing |
| Gemini 2.0 Vision | ~$0.01–$0.05 | Lowest cost, high quality |

**Recommendation:** Use Gemini 2.0 as primary if cost matters; OpenAI or Anthropic for quality.

## Future Enhancements

- [ ] Add provider-specific prompt templates for quality tuning
- [ ] Cache vision analysis results per product image hash
- [ ] Add quality scoring to detect low-confidence analyses
- [ ] Support additional models (Claude 3 Opus, other vision APIs)
- [ ] Parallel provider execution (race condition, use fastest)
