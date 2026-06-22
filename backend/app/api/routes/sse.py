import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.run_manager import run_manager
from app.pipeline.manager import pipeline_manager

router = APIRouter(prefix="/api/runs", tags=["sse"])


@router.get("/{run_id}/events")
async def stream_events(run_id: str) -> StreamingResponse:
    # Validate run exists before streaming; convert missing-run to 404.
    try:
        run_manager.get_metadata(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found.")

    async def event_stream():
        async for event in pipeline_manager.attach(run_id):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: {\"event\": \"stream_end\", \"data\": {}}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
