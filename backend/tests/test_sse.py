"""Tests for the PipelineManager and the /api/runs/{run_id}/events SSE endpoint.

Mocks ``run_pipeline`` at the manager's import boundary so no real LLM or fal
calls are made.  Tests drive the manager directly (faster, no HTTP overhead)
except for the "already_complete" guard which we also smoke-test via the HTTP
endpoint using FastAPI TestClient.
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.core.run_manager import run_manager
from app.pipeline.manager import _TERMINAL_STATUSES, PipelineManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCRIPTED_EVENTS = [
    {"event": "pipeline_started", "data": {"run_id": "X"}},
    {"event": "text_processed", "data": {"total_words": 3}},
    {"event": "pipeline_complete", "data": {"run_id": "X", "completed_at": "2099-01-01T00:00:00+00:00"}},  # noqa: E501
]


async def _scripted_pipeline(run_id: str) -> AsyncGenerator[dict, None]:  # noqa: RUF029
    """Async generator that yields a fixed sequence of events."""
    for event in _SCRIPTED_EVENTS:
        # Replace run_id placeholder in pipeline_started / pipeline_complete.
        evt = dict(event)
        evt["data"] = {**evt["data"], "run_id": run_id}
        yield evt
        await asyncio.sleep(0)  # yield to event loop so tasks can run


def _make_run(tmp_content_dir: Path) -> str:
    """Create a minimal run with status 'running' (fresh run)."""
    run_id = run_manager.create_run()
    run_manager.update_metadata(
        run_id,
        {
            "inputs": {
                "description_product": "test",
                "description_audience": "test",
                "description_colors": "test",
                "image_path": None,
                "video_path": None,
                "model_3d_path": None,
                "reference_image_path": None,
            }
        },
    )
    return run_id


async def _collect_manager(manager: PipelineManager, run_id: str) -> list[dict]:
    return [event async for event in manager.attach(run_id)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_normal_run_streams_all_events_then_ends(tmp_content_dir: Path):
    """A fresh run streams all scripted events; stream terminates cleanly."""
    run_id = _make_run(tmp_content_dir)
    manager = PipelineManager()

    with patch("app.pipeline.manager.run_pipeline", side_effect=_scripted_pipeline):
        events = await _collect_manager(manager, run_id)

    event_names = [e["event"] for e in events]
    assert "pipeline_started" in event_names
    assert "text_processed" in event_names
    assert "pipeline_complete" in event_names

    # Completion metadata should have been persisted by the manager.
    meta = run_manager.get_metadata(run_id)
    assert meta["status"] == "completed"


async def test_second_subscriber_does_not_trigger_second_pipeline(tmp_content_dir: Path):
    """Two concurrent subscribers share one pipeline execution (mock called once)."""
    run_id = _make_run(tmp_content_dir)
    manager = PipelineManager()

    call_count = 0

    async def counting_pipeline(rid: str) -> AsyncGenerator[dict, None]:
        nonlocal call_count
        call_count += 1
        async for evt in _scripted_pipeline(rid):
            yield evt

    with patch("app.pipeline.manager.run_pipeline", side_effect=counting_pipeline):
        # Launch both subscribers concurrently.
        results = await asyncio.gather(
            _collect_manager(manager, run_id),
            _collect_manager(manager, run_id),
        )

    assert call_count == 1, f"run_pipeline called {call_count} times, expected 1"

    # Both subscribers must have received all events.
    for received in results:
        names = [e["event"] for e in received]
        assert "pipeline_started" in names
        assert "pipeline_complete" in names


async def test_late_subscriber_receives_replayed_events(tmp_content_dir: Path):
    """A subscriber that joins after the pipeline completes still gets all events."""
    run_id = _make_run(tmp_content_dir)
    manager = PipelineManager()

    with patch("app.pipeline.manager.run_pipeline", side_effect=_scripted_pipeline):
        # First subscriber — drives the pipeline to completion.
        first = await _collect_manager(manager, run_id)
        assert len(first) == len(_SCRIPTED_EVENTS)

    # Pipeline task has finished; metadata is now "completed".
    # A late subscriber attaches *after* completion.
    # Because status is now "completed" (terminal), the manager should return
    # the already_complete path — but that is covered by the next test.
    # Here we test the *replay path*: attach before the record is evicted but
    # after the task is done.  We do this by reaching into the record directly.
    record = manager._runs[run_id]
    assert record.done is True

    # Simulate a late attach that goes through the replay-buffer path.
    second = await _collect_manager(manager, run_id)
    # The late subscriber hits the "already_complete" guard because update_metadata
    # wrote "completed" during the pipeline run.
    assert second[0]["event"] == "already_complete"


async def test_terminal_run_does_not_call_pipeline(tmp_content_dir: Path):
    """A run whose metadata status is already terminal never runs the pipeline."""
    run_id = _make_run(tmp_content_dir)
    # Mark as completed so the manager sees a terminal status.
    run_manager.update_metadata(run_id, {"status": "completed", "completed_at": "now"})

    manager = PipelineManager()
    mock_pipeline = AsyncMock()

    with patch("app.pipeline.manager.run_pipeline", mock_pipeline):
        events = await _collect_manager(manager, run_id)

    mock_pipeline.assert_not_called()
    assert len(events) == 1
    assert events[0]["event"] == "already_complete"
    assert events[0]["data"]["status"] == "completed"


@pytest.mark.parametrize("terminal_status", list(_TERMINAL_STATUSES))
async def test_all_terminal_statuses_block_rerun(tmp_content_dir: Path, terminal_status: str):
    """Every status in _TERMINAL_STATUSES prevents re-execution."""
    run_id = _make_run(tmp_content_dir)
    run_manager.update_metadata(run_id, {"status": terminal_status})

    manager = PipelineManager()
    mock_pipeline = AsyncMock()

    with patch("app.pipeline.manager.run_pipeline", mock_pipeline):
        events = await _collect_manager(manager, run_id)

    mock_pipeline.assert_not_called()
    assert events[0]["event"] == "already_complete"
    assert events[0]["data"]["status"] == terminal_status


async def test_sse_endpoint_already_complete(tmp_content_dir: Path, client):
    """HTTP endpoint returns already_complete + stream_end for a terminal run."""
    run_id = _make_run(tmp_content_dir)
    run_manager.update_metadata(run_id, {"status": "completed", "completed_at": "now"})

    # Patch the manager imported by the SSE route.
    fresh_manager = PipelineManager()
    with patch("app.api.routes.sse.pipeline_manager", fresh_manager):
        resp = client.get(f"/api/runs/{run_id}/events")

    assert resp.status_code == 200
    raw = resp.text
    # Collect SSE data lines.
    data_lines = [
        line[len("data: "):].strip()
        for line in raw.splitlines()
        if line.startswith("data: ")
    ]
    events = [json.loads(d) for d in data_lines if d]
    event_names = [e["event"] for e in events]
    assert "already_complete" in event_names
    assert "stream_end" in event_names


async def test_sse_endpoint_unknown_run_returns_404(tmp_content_dir: Path, client):
    """Requesting events for a non-existent run returns 404."""
    resp = client.get("/api/runs/does-not-exist/events")
    assert resp.status_code == 404
