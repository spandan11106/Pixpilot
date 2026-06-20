"""Ingestion pipeline — reads a run's inputs and produces vision-ready payloads.

Flow:

    start → process_text → process_image → process_reference → process_video
          → process_model → finalize → complete

The required product image halts the run on failure (routes to END with a
``pipeline_error`` event). The optional reference image, video and 3D model are
non-fatal: a missing or failed input emits a ``*_skipped`` / ``*_failed`` event
and the run continues.
Full base64 payloads are written to ``content/<run_id>/processed/ingestion.json``
and kept out of both the SSE stream and ``run_metadata.json``.
"""

import json
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from app.core.run_manager import run_manager
from app.core.settings import settings
from app.pipeline.agents.summary_agent import generate_image_prompt, generate_summary_card
from app.pipeline.agents.vision_orchestrator import get_orchestrator
from app.pipeline.processors import (
    process_image,
    process_model,
    process_text,
    process_video,
)

logger = logging.getLogger(__name__)


class PipelineState(TypedDict):
    run_id: str
    events: list[dict]
    results: dict
    failed: bool


def _emit(state: PipelineState, event: str, data: dict, **updates: Any) -> dict:
    entry = {"event": event, "data": data}
    return {"events": state["events"] + [entry], **updates}


def _inputs(run_id: str) -> dict:
    return run_manager.get_metadata(run_id).get("inputs", {})


def _abs_path(run_id: str, rel_path: str) -> Any:
    return run_manager.get_content_dir() / run_id / rel_path


def _cached_result(run_id: str, key: str) -> dict | None:
    """Return a successful upload-time processing result, if one was cached.

    Assets processed at upload time leave their result in
    ``processed/cache/<key>.json``; reusing it lets the pipeline skip the sidecar
    work. Only successful caches are reused — a missing or errored cache means the
    node processes the input fresh.
    """
    cache_path = run_manager.get_content_dir() / run_id / "processed" / "cache" / f"{key}.json"
    if not cache_path.exists():
        return None
    try:
        cached = json.loads(cache_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if cached.get("status") != "success":
        return None
    return cached.get("result")


def start_node(state: PipelineState) -> dict:
    return _emit(state, "pipeline_started", {"run_id": state["run_id"]})


def process_text_node(state: PipelineState) -> dict:
    inputs = _inputs(state["run_id"])
    fields = {
        "product": inputs.get("description_product", ""),
        "audience": inputs.get("description_audience", ""),
        "colors": inputs.get("description_colors", ""),
    }
    text_result = {key: process_text(value) for key, value in fields.items()}
    results = {**state["results"], "text": text_result}
    total_words = sum(part["metrics"]["word_count"] for part in text_result.values())
    return _emit(
        state,
        "text_processed",
        {"fields": list(fields), "total_words": total_words},
        results=results,
    )


def process_image_node(state: PipelineState) -> dict:
    run_id = state["run_id"]
    image_rel = _inputs(run_id).get("image_path")
    if not image_rel:
        run_manager.update_metadata(run_id, {"status": "failed"})
        return _emit(
            state,
            "pipeline_error",
            {"stage": "image", "error": "No product image found for this run."},
            failed=True,
        )
    cached = _cached_result(run_id, "product_image")
    try:
        image_result = cached or process_image(_abs_path(run_id, image_rel))
    except Exception as e:  # noqa: BLE001 - any failure of the required image halts the run
        run_manager.update_metadata(run_id, {"status": "failed"})
        return _emit(
            state,
            "pipeline_error",
            {"stage": "image", "error": str(e)},
            failed=True,
        )
    results = {**state["results"], "image": image_result}
    return _emit(
        state,
        "image_processed",
        {"metrics": image_result["metrics"], "cached": cached is not None},
        results=results,
    )


def process_reference_node(state: PipelineState) -> dict:
    run_id = state["run_id"]
    reference_rel = _inputs(run_id).get("reference_image_path")
    if not reference_rel:
        return _emit(state, "reference_skipped", {"reason": "no reference image provided"})

    cached = _cached_result(run_id, "reference_image")
    try:
        reference_result = cached or process_image(_abs_path(run_id, reference_rel))
    except Exception as e:  # noqa: BLE001 - reference image is optional; failure is non-fatal
        return _emit(state, "reference_failed", {"error": str(e)})

    results = {**state["results"], "reference_image": reference_result}
    return _emit(
        state,
        "reference_processed",
        {"metrics": reference_result["metrics"], "cached": cached is not None},
        results=results,
    )


async def process_video_node(state: PipelineState) -> dict:
    run_id = state["run_id"]
    video_rel = _inputs(run_id).get("video_path")
    if not video_rel:
        return _emit(state, "video_skipped", {"reason": "no video provided"})

    cached = _cached_result(run_id, "video")
    try:
        video_result = cached or await process_video(
            _abs_path(run_id, video_rel), settings.ffmpeg_sidecar_url
        )
    except Exception as e:  # noqa: BLE001 - video is optional; failure is non-fatal
        return _emit(state, "video_failed", {"error": str(e)})

    results = {**state["results"], "video": video_result}
    return _emit(
        state,
        "video_processed",
        {"frame_count": video_result["metrics"]["frame_count"], "cached": cached is not None},
        results=results,
    )


async def process_model_node(state: PipelineState) -> dict:
    run_id = state["run_id"]
    model_rel = _inputs(run_id).get("model_3d_path")
    if not model_rel:
        return _emit(state, "model_skipped", {"reason": "no 3D model provided"})

    cached = _cached_result(run_id, "model_3d")
    try:
        model_result = cached or await process_model(
            _abs_path(run_id, model_rel), settings.renderer_sidecar_url
        )
    except Exception as e:  # noqa: BLE001 - 3D model is optional; failure is non-fatal
        return _emit(state, "model_failed", {"error": str(e)})

    results = {**state["results"], "model_3d": model_result}
    return _emit(
        state,
        "model_processed",
        {
            "thumbnail_count": model_result["metrics"]["thumbnail_count"],
            "cached": cached is not None,
        },
        results=results,
    )


def finalize_node(state: PipelineState) -> dict:
    run_id = state["run_id"]
    results = state["results"]

    processed_dir = run_manager.get_content_dir() / run_id / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    artifact = processed_dir / "ingestion.json"
    artifact.write_text(json.dumps(results, indent=2))

    # Lean summary in run_metadata.json — pointers and counts, never the blobs.
    summary = {
        "artifact_path": "processed/ingestion.json",
        "text_fields": list(results.get("text", {})),
        "image_processed": "image" in results,
        "reference_image_processed": "reference_image" in results,
        "video_frame_count": results.get("video", {}).get("metrics", {}).get("frame_count", 0),
        "model_3d_thumbnail_count": results.get("model_3d", {})
        .get("metrics", {})
        .get("thumbnail_count", 0),
    }
    run_manager.update_metadata(run_id, {"ingestion": summary})
    return _emit(state, "ingestion_complete", summary)


async def vision_analysis_node(state: PipelineState) -> dict:
    """Analyze processed media and produce product profile."""
    run_id = state["run_id"]
    results = state["results"]

    # Extract base64 payloads from ingestion results
    product_image = results.get("image", {}).get("image_payload")
    reference_image = results.get("reference_image", {}).get("image_payload")

    # Extract image payloads from video frames
    video_frames = []
    if "video" in results:
        frames = results["video"].get("frames", [])
        video_frames = [frame.get("image_payload") for frame in frames if "image_payload" in frame]

    # Extract image payloads from 3D model thumbnails
    model_thumbnails = []
    if "model_3d" in results:
        thumbnails = results["model_3d"].get("thumbnails", [])
        model_thumbnails = [thumb.get("image_payload") for thumb in thumbnails if "image_payload" in thumb]

    # Try vision analysis with fallback
    if not product_image:
        logger.warning(f"Run {run_id}: No product image available for vision analysis")
        return _emit(
            state,
            "vision_analysis_skipped",
            {"reason": "No product image processed"},
        )

    product_profile = await get_orchestrator().analyze(
        product_image, reference_image, video_frames or None, model_thumbnails or None
    )

    if product_profile is None:
        return _emit(
            state,
            "vision_analysis_failed",
            {
                "reason": "All vision providers failed",
                "action_required": "User must choose to skip or retry",
            },
        )

    # Store in run_metadata.json
    run_manager.update_metadata(
        run_id, {"agent_states": {"product_profile": product_profile}}
    )
    logger.info(f"Run {run_id}: Vision analysis complete using {product_profile['provider_used']}")

    results = {**state["results"], "product_profile": product_profile}
    return _emit(
        state,
        "vision_analyzed",
        {
            "provider": product_profile["provider_used"],
            "completeness": product_profile["analysis_completeness"],
        },
        results=results,
    )


async def summary_agent_node(state: PipelineState) -> dict:
    """Call 1: Input Summary Card. Call 2: structured Image Gen Prompt."""
    run_id = state["run_id"]
    results = state["results"]
    text_results = results.get("text", {})
    product_profile = results.get("product_profile")
    steering = run_manager.get_metadata(run_id).get("steering", {})

    # ── Call 1: Summary Card ──────────────────────────────────────────────────
    try:
        summary_card = await generate_summary_card(text_results, product_profile)
    except Exception as e:
        logger.error(f"Run {run_id}: Summary card generation failed: {e}")
        return _emit(state, "summary_failed", {"error": str(e)})

    run_manager.update_metadata(run_id, {"agent_states": {"summary_card": summary_card}})
    logger.info(f"Run {run_id}: Summary card generated (vision_available={summary_card.get('vision_available')})")

    # ── Call 2: Image Generation Prompt ──────────────────────────────────────
    try:
        creative_blueprint = await generate_image_prompt(summary_card, steering)
    except Exception as e:
        logger.warning(f"Run {run_id}: Image prompt generation failed: {e}")
        run_manager.update_metadata(run_id, {"agent_states": {"summary_card": summary_card}})
        results = {**results, "summary_card": summary_card}
        return _emit(
            state,
            "image_prompt_failed",
            {"error": str(e)},
            results=results,
        )

    run_manager.update_metadata(
        run_id,
        {"agent_states": {"summary_card": summary_card, "creative_blueprint": creative_blueprint}},
    )
    logger.info(f"Run {run_id}: Image generation prompt ready")

    results = {**results, "summary_card": summary_card, "creative_blueprint": creative_blueprint}
    return _emit(
        state,
        "summary_complete",
        {
            "vision_available": summary_card.get("vision_available", False),
            "product_name": summary_card.get("product_name"),
            "summary_card": summary_card,
        },
        results=results,
    )


def complete_node(state: PipelineState) -> dict:
    return _emit(
        state,
        "pipeline_complete",
        {"run_id": state["run_id"], "completed_at": datetime.now(UTC).isoformat()},
    )


def _route_after_image(state: PipelineState) -> str:
    return END if state["failed"] else "process_reference"


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
    builder.add_node("complete", complete_node)

    builder.set_entry_point("start")
    builder.add_edge("start", "process_text")
    builder.add_edge("process_text", "process_image")
    builder.add_conditional_edges(
        "process_image", _route_after_image, {"process_reference": "process_reference", END: END}
    )
    builder.add_edge("process_reference", "process_video")
    builder.add_edge("process_video", "process_model")
    builder.add_edge("process_model", "finalize")
    builder.add_edge("finalize", "vision_analysis")
    builder.add_edge("vision_analysis", "summary_agent")
    builder.add_edge("summary_agent", "complete")
    builder.add_edge("complete", END)
    return builder.compile()


pipeline = build_graph()


async def run_pipeline(run_id: str) -> AsyncGenerator[dict, None]:
    """Execute the pipeline and yield SSE events as each node emits them."""
    state: PipelineState = {"run_id": run_id, "events": [], "results": {}, "failed": False}
    async for chunk in pipeline.astream(state, stream_mode="updates"):
        for node_update in chunk.values():
            new_events = node_update.get("events", [])
            if new_events:
                yield new_events[-1]
