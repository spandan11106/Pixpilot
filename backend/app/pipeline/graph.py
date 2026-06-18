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
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from app.core.run_manager import run_manager
from app.core.settings import settings
from app.pipeline.processors import (
    process_image,
    process_model,
    process_text,
    process_video,
)


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
    try:
        image_result = process_image(_abs_path(run_id, image_rel))
    except Exception as e:  # noqa: BLE001 - any failure of the required image halts the run
        run_manager.update_metadata(run_id, {"status": "failed"})
        return _emit(
            state,
            "pipeline_error",
            {"stage": "image", "error": str(e)},
            failed=True,
        )
    results = {**state["results"], "image": image_result}
    return _emit(state, "image_processed", {"metrics": image_result["metrics"]}, results=results)


def process_reference_node(state: PipelineState) -> dict:
    run_id = state["run_id"]
    reference_rel = _inputs(run_id).get("reference_image_path")
    if not reference_rel:
        return _emit(state, "reference_skipped", {"reason": "no reference image provided"})

    try:
        reference_result = process_image(_abs_path(run_id, reference_rel))
    except Exception as e:  # noqa: BLE001 - reference image is optional; failure is non-fatal
        return _emit(state, "reference_failed", {"error": str(e)})

    results = {**state["results"], "reference_image": reference_result}
    return _emit(
        state,
        "reference_processed",
        {"metrics": reference_result["metrics"]},
        results=results,
    )


async def process_video_node(state: PipelineState) -> dict:
    run_id = state["run_id"]
    video_rel = _inputs(run_id).get("video_path")
    if not video_rel:
        return _emit(state, "video_skipped", {"reason": "no video provided"})

    try:
        video_result = await process_video(
            _abs_path(run_id, video_rel), settings.ffmpeg_sidecar_url
        )
    except Exception as e:  # noqa: BLE001 - video is optional; failure is non-fatal
        return _emit(state, "video_failed", {"error": str(e)})

    results = {**state["results"], "video": video_result}
    return _emit(
        state,
        "video_processed",
        {"frame_count": video_result["metrics"]["frame_count"]},
        results=results,
    )


async def process_model_node(state: PipelineState) -> dict:
    run_id = state["run_id"]
    model_rel = _inputs(run_id).get("model_3d_path")
    if not model_rel:
        return _emit(state, "model_skipped", {"reason": "no 3D model provided"})

    try:
        model_result = await process_model(
            _abs_path(run_id, model_rel), settings.renderer_sidecar_url
        )
    except Exception as e:  # noqa: BLE001 - 3D model is optional; failure is non-fatal
        return _emit(state, "model_failed", {"error": str(e)})

    results = {**state["results"], "model_3d": model_result}
    return _emit(
        state,
        "model_processed",
        {"thumbnail_count": model_result["metrics"]["thumbnail_count"]},
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
    builder.add_edge("finalize", "complete")
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
