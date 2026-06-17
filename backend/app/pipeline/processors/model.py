"""3D model processing for ingestion.

Delegates perspective rendering to the Three.js Docker sidecar, which returns 4
PNG thumbnails (front, three-quarter, side, back). Each PNG is then run through
the image processor to produce base64 data URIs. The raw model is deleted after
a successful render (the thumbnails are all the vision pipeline needs).

Accepted inputs:

- ``.glb`` / ``.gltf`` / ``.obj`` — rendered directly.
- ``.zip`` — a multi-file glTF bundle (``.gltf`` + ``.bin`` + ``textures/``). It is
  extracted (with zip-slip protection) and the ``.gltf``/``.glb`` entrypoint inside
  is rendered, so its sibling buffers and textures resolve on disk.

The renderer and backend share the same content mount, so an extracted bundle is
visible to the sidecar at the same path. Unsupported formats (e.g. USDZ) are
rejected by the sidecar with a 400, surfacing here as a ``ModelProcessingError``.
"""

import shutil
import zipfile
from pathlib import Path
from typing import Any

import httpx

from app.pipeline.processors.image import process_image

_REQUEST_TIMEOUT = 300.0  # loading + rendering a large model can take a while
_ENTRYPOINT_EXTS = (".gltf", ".glb")


class ModelProcessingError(RuntimeError):
    """Raised when 3D rendering or thumbnail processing fails."""


def _safe_extract(zip_path: Path, dest: Path) -> None:
    """Extract a zip into ``dest``, rejecting any member that escapes it."""
    dest.mkdir(parents=True, exist_ok=True)
    dest_root = dest.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            target = (dest / member).resolve()
            if target != dest_root and dest_root not in target.parents:
                raise ModelProcessingError(
                    f"Unsafe path in zip bundle: {member!r}"
                )
        zf.extractall(dest)


def _find_entrypoint(root: Path) -> Path:
    """Return the shallowest .gltf/.glb in an extracted bundle."""
    candidates = [
        p
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in _ENTRYPOINT_EXTS
    ]
    if not candidates:
        raise ModelProcessingError(
            "Zip bundle contains no .gltf or .glb entrypoint."
        )
    # Prefer the least-nested file, tie-break alphabetically for determinism.
    return min(candidates, key=lambda p: (len(p.relative_to(root).parts), str(p)))


async def process_model(
    file_path: str | Path,
    sidecar_url: str,
    *,
    delete_raw: bool = True,
) -> dict[str, Any]:
    """Render perspective thumbnails via the renderer sidecar and encode them."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"3D model file not found: {path}")

    # A zip bundle is extracted next to itself; the glTF entrypoint inside is
    # what we actually render, with its buffers/textures resolved on disk.
    extract_dir: Path | None = None
    if path.suffix.lower() == ".zip":
        extract_dir = path.parent / f"{path.stem}_extracted"
        _safe_extract(path, extract_dir)
        render_path = _find_entrypoint(extract_dir)
    else:
        render_path = path

    endpoint = f"{sidecar_url.rstrip('/')}/render-3d"
    payload = {"model_path": str(render_path)}

    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.post(endpoint, json=payload)
    except httpx.HTTPError as e:
        raise ModelProcessingError(f"Renderer sidecar unreachable: {e}") from e

    if response.status_code != 200:
        raise ModelProcessingError(
            f"Renderer sidecar returned {response.status_code}: {response.text}"
        )

    body = response.json()
    thumbnail_paths = body.get("thumbnails", [])
    if not thumbnail_paths:
        raise ModelProcessingError("Renderer produced no thumbnails for the model.")

    thumbnails = [process_image(thumb_path) for thumb_path in thumbnail_paths]

    if delete_raw:
        path.unlink(missing_ok=True)
        if extract_dir is not None:
            shutil.rmtree(extract_dir, ignore_errors=True)

    return {
        "status": "success",
        "filename": path.name,
        "metrics": {
            "thumbnail_count": len(thumbnails),
            "raw_model_deleted": delete_raw,
            **body.get("metrics", {}),
        },
        "thumbnails": thumbnails,
    }
