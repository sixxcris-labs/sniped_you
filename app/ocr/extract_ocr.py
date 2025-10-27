import os
import sys
import json
from datetime import datetime, timezone
from app.ocr.easyocr_engine import run_easyocr
from app.ocr.paddleocr_wrapper import run_paddleocr
# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

def run_pipeline(image_path: str, engine: str = "easyocr") -> dict:
    """
    Unified OCR pipeline.
    engine: "easyocr" or "paddleocr"
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    if engine == "easyocr":
        result = run_easyocr(image_path)
    elif engine == "paddleocr":
        result = run_paddleocr(image_path)
    else:
        raise ValueError(f"Unsupported engine: {engine}")

    structured = {
        "image": image_path,
        "text": result.get("text", ""),
        "fields": result.get("fields", {}),
        "confidence": result.get("confidence", 0.0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return structured


def batch_pipeline(
    input_dir: str,
    engine: str = "easyocr",
    output_file: str = "data/output/ocr_results.json",
):
    """
    Batch process all images in input_dir and save results to output_file.
    """
    results = []

    for root, _, files in os.walk(input_dir):
        for name in files:
            if name.lower().endswith((".png", ".jpg", ".jpeg")):
                path = os.path.join(root, name)
                try:
                    res = run_pipeline(path, engine)
                    results.append(res)
                    print(f"[{engine}] processed {name}")
                except Exception as e:
                    print(f"[{engine}] error {name} {e}")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Saved {len(results)} results -> {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run OCR pipeline")
    parser.add_argument(
        "--image-dir", default="data/screenshots", help="Directory with images"
    )
    parser.add_argument(
        "--engine",
        choices=["easyocr", "paddleocr"],
        default="easyocr",
        help="OCR engine",
    )
    parser.add_argument(
        "--output", default="data/output/ocr_results.json", help="Output JSON file"
    )
    args = parser.parse_args()

    batch_pipeline(args.image_dir, args.engine, args.output)
