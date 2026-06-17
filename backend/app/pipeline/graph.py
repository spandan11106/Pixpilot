"""LangGraph pipeline stub — Milestone 0. Real agent nodes added in Milestones 1–3."""

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict


class PipelineState(TypedDict):
    run_id: str
    events: list[dict]


def _emit(state: PipelineState, event: str, data: dict) -> dict:
    entry = {"event": event, "data": data}
    return {"events": state["events"] + [entry]}


def start_node(state: PipelineState) -> dict:
    return _emit(state, "pipeline_started", {"run_id": state["run_id"]})


def complete_node(state: PipelineState) -> dict:
    return _emit(
        state,
        "pipeline_complete",
        {"run_id": state["run_id"], "completed_at": datetime.now(timezone.utc).isoformat()},
    )


def build_graph() -> StateGraph:
    builder = StateGraph(PipelineState)
    builder.add_node("start", start_node)
    builder.add_node("complete", complete_node)
    builder.set_entry_point("start")
    builder.add_edge("start", "complete")
    builder.add_edge("complete", END)
    return builder.compile()


pipeline = build_graph()


async def run_pipeline(run_id: str) -> AsyncGenerator[dict, None]:
    """Execute the pipeline and yield SSE events as they are emitted."""
    state: PipelineState = {"run_id": run_id, "events": []}
    result = await asyncio.to_thread(pipeline.invoke, state)
    for event in result["events"]:
        yield event
