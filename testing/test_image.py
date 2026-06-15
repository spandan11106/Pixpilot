import base64
import os 
from io import BytesIO
from typing import Dict, Any
from PIL import Image
from data_processing.image import process_image

if __name__ == "__main__":
    # Setup dummy directories for testing execution
    test_dir = "./testing_input"
    test_image_path = f"{test_dir}/test_product.png"
    os.makedirs(test_dir, exist_ok=True)
    
    # Generate a lightweight mock image if one doesn't exist
    if not os.path.exists(test_image_path):
        mock_img = Image.new("RGBA", (3000, 2000), color=(26, 26, 26, 255)) # Dark Charcoal base
        mock_img.save(test_image_path)
        print(f"Created a mock high-res 3000x2000 image at: {test_image_path}")

    try:
        result = process_image(test_image_path, max_longest_edge=1024)
        print(f"\n✅ Successfully Processed Image Asset: {result['filename']}")
        print(f"📊 Orig Res: {result['metrics']['original_resolution']} -> New Res: {result['metrics']['processed_resolution']}")
        print(f"📦 Encoded Payload Size: {result['metrics']['payload_size_kb']} KB")
        print(f"🔗 Data URI Prefix: {result['image_payload'][:50]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
