import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.run_manager import run_manager
from app.pipeline.graph import run_pipeline

router = APIRouter(prefix="/api/runs", tags=["sse"])


@router.get("/{run_id}/events")
async def stream_events(run_id: str) -> StreamingResponse:
    # Validate run exists before streaming
    run_manager.get_metadata(run_id)

    async def event_stream():
        async for event in run_pipeline(run_id):
            yield f"data: {json.dumps(event)}\n\n"
            # Update metadata on completion event
            if event["event"] == "pipeline_complete":
                run_manager.update_metadata(
                    run_id,
                    {
                        "status": "completed",
                        "completed_at": event["data"].get("completed_at"),
                    },
                )
        yield "data: {\"event\": \"stream_end\", \"data\": {}}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
