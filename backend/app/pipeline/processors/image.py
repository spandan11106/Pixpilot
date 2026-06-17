"""Image processing for ingestion.

Validates an image file, scales it to fit a token-friendly bound, and encodes it
as a JPEG base64 data URI suitable for vision-model consumption.
"""

import base64
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def process_image(file_path: str | Path, max_longest_edge: int = 1024) -> dict[str, Any]:
    """Validate, downscale, and base64-encode an image into a data URI."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    ext = path.suffix.lower()
    if ext not in VALID_EXTENSIONS:
        raise ValueError(
            f"Unsupported image format '{ext}'. Must be one of: {sorted(VALID_EXTENSIONS)}"
        )

    try:
        with Image.open(path) as img:
            orig_width, orig_height = img.size

            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img.thumbnail((max_longest_edge, max_longest_edge), Image.Resampling.LANCZOS)
            new_width, new_height = img.size

            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            base64_string = base64.b64encode(buffered.getvalue()).decode("utf-8")
    except (FileNotFoundError, ValueError):
        raise
    except Exception as e:  # noqa: BLE001 - surface any decode/encode failure uniformly
        raise RuntimeError(f"Image corruption or processing failure: {e}") from e

    return {
        "status": "success",
        "filename": path.name,
        "metrics": {
            "original_resolution": f"{orig_width}x{orig_height}",
            "processed_resolution": f"{new_width}x{new_height}",
            "payload_size_kb": round(len(base64_string) / 1024, 2),
        },
        "image_payload": f"data:image/jpeg;base64,{base64_string}",
    }
