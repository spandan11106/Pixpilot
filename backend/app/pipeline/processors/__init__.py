"""Ingestion processors — turn raw run inputs into clean, vision-ready payloads.

These mirror the standalone ``data_processing/`` modules but operate inside the
backend service (which has its own Docker context and cannot import the repo-root
package). ``text`` works on strings, ``image`` on a file path, and ``video``
orchestrates the FFmpeg sidecar then reuses the image processor on each frame.
"""

from app.pipeline.processors.image import process_image
from app.pipeline.processors.text import process_text
from app.pipeline.processors.video import process_video

__all__ = ["process_text", "process_image", "process_video"]
