import base64
import os 
from io import BytesIO
from typing import Dict, Any 
from PIL import Image 

def process_image(file_path: str, max_longest_edge = 1024) -> Dict[str, Any]:
    """
    Validates a image file, scales it to optimize token boundaries,
    and encodes it into a standard Base64 data URI for vision models.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Image file not found: {file_path}")

    valid_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    ext = os.path.splitext(file_path)[1].lower()

    if ext not in valid_extensions:
        raise ValueError(f"Unsupported image format '{ext}'. Must be one of: {valid_extensions}")

    try :
        with Image.open(file_path) as img:
            orig_width, orig_height = img.size

            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img.thumbnail((max_longest_edge, max_longest_edge), Image.Resampling.LANCZOS)
            new_width, new_height = img.size

            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_bytes = buffered.getvalue()

            base64_string = base64.b64encode(img_bytes).decode("utf-8")
            data_uri = f"data:image/jpeg;base64,{base64_string}"

            return {
                "status": "success",
                "filename": os.path.basename(file_path),
                "metrics": {
                    "original_resolution": f"{orig_width}x{orig_height}",
                    "processed_resolution": f"{new_width}x{new_height}",
                    "payload_size_kb": round(len(base64_string) / 1024, 2)
                },
                "image_payload": data_uri
            }
    except Exception as e:
        raise RuntimeError(f"Image corruption or processing failure: {str(e)}")


