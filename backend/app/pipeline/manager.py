"""In-process pipeline execution manager.

Decouples pipeline execution from SSE HTTP connections so that:
- A client disconnect does NOT cancel the running pipeline.
- Concurrent/repeated ``/events`` connections for the same run share one execution.
- Events emitted before a late subscriber connects are replayed from an in-memory buffer.
- Runs whose persisted status is already terminal are never re-executed.

Design
------
``PipelineManager`` holds a module-level dict ``_runs`` keyed by ``run_id``.
Each entry is a ``_RunRecord`` that stores:
- ``task``    — the ``asyncio.Task`` running the pipeline (kept to prevent GC).
- ``buffer``  — list of events already emitted (replay buffer).
- ``queues``  — list of ``asyncio.Queue`` objects, one per active subscriber.
- ``done``    — set to ``True`` when the background task has finished.

Flow for a new connection
~~~~~~~~~~~~~~~~~~~~~~~~~
1. ``attach(run_id)`` checks persisted metadata status; terminal → yield the
   ``already_complete`` sentinel and return immediately.
2. If no record exists the pipeline is started as a background asyncio task.
3. Replay buffered events to the new subscriber, then drain its queue until the
   sentinel ``_DONE`` is received.

The background task pushes every event to the buffer and to every subscriber
queue, and enqueues ``_DONE`` into each queue when it finishes (or fails).
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

from app.core.run_manager import run_manager
from app.pipeline.graph import run_pipeline

logger = logging.getLogger(__name__)

# Sentinel placed into subscriber queues to signal end-of-stream.
_DONE = object()

# Statuses that mean the run is terminal and must not be re-executed.
_TERMINAL_STATUSES = {"completed", "failed", "image_generated"}


@dataclass
class _RunRecord:
    task: asyncio.Task  # type: ignore[type-arg]
    buffer: list[dict] = field(default_factory=list)
    queues: list[asyncio.Queue] = field(default_factory=list)  # type: ignore[type-arg]
    done: bool = False


class PipelineManager:
    """Singleton that manages one background task per run_id."""

    def __init__(self) -> None:
        self._runs: dict[str, _RunRecord] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def attach(self, run_id: str) -> AsyncGenerator[dict, None]:
        """Yield pipeline events for *run_id*.

        If the run is already terminal (per persisted metadata) yield the
        ``already_complete`` event and return without re-executing the pipeline.

        If the pipeline is already in-flight, replay buffered events then wait
        for new ones.  If this is the first subscriber, start the pipeline as a
        background task first.
        """
        # Guard: terminal run → emit sentinel and exit immediately.
        meta = run_manager.get_metadata(run_id)
        if meta.get("status") in _TERMINAL_STATUSES:
            yield {"event": "already_complete", "data": {"status": meta["status"]}}
            return

        # Ensure exactly one background task exists for this run_id.
        if run_id not in self._runs:
            self._runs[run_id] = self._start(run_id)

        record = self._runs[run_id]

        # Build a per-subscriber queue and replay events emitted so far.
        q: asyncio.Queue = asyncio.Queue()  # type: ignore[type-arg]

        # Add the queue *before* replaying the buffer so we don't miss events
        # emitted between the replay and the queue being registered.
        record.queues.append(q)

        # Replay already-buffered events.
        for event in list(record.buffer):
            yield event

        # If the task finished before we attached, drain immediately.
        if record.done:
            record.queues.remove(q)
            return

        # Wait for new events from the background task.
        try:
            while True:
                item = await q.get()
                if item is _DONE:
                    break
                yield item
        finally:
            # Always clean up the queue reference even on client disconnect.
            if q in record.queues:
                record.queues.remove(q)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _start(self, run_id: str) -> _RunRecord:
        """Create a ``_RunRecord`` and schedule the pipeline background task."""
        record = _RunRecord(task=None)  # type: ignore[arg-type]
        # Create the coroutine before assigning so the record exists in _runs
        # before the task can run (prevents a race on very fast event loops).
        task = asyncio.ensure_future(self._run(run_id, record))
        record.task = task
        return record

    async def _run(self, run_id: str, record: _RunRecord) -> None:
        """Background coroutine: drives run_pipeline and fans out events."""
        try:
            async for event in run_pipeline(run_id):
                record.buffer.append(event)
                for q in list(record.queues):
                    await q.put(event)
                # Persist completion status here (not in SSE handler) so the
                # write happens regardless of whether any client is connected.
                if event["event"] == "pipeline_complete":
                    run_manager.update_metadata(
                        run_id,
                        {
                            "status": "completed",
                            "completed_at": event["data"].get("completed_at"),
                        },
                    )
        except Exception:
            logger.exception("Pipeline task for run %s raised an uncaught exception", run_id)
        finally:
            record.done = True
            for q in list(record.queues):
                await q.put(_DONE)
            # Keep the record in _runs so late subscribers still get replays.
            # A production system would evict old records on a TTL; for now the
            # lifetime matches the process.


pipeline_manager = PipelineManager()
