"""Download helmet YOLO model from Hugging Face Hub.

Downloads iam-tsr/yolov8n-helmet-detection (best.pt) and saves as
backend/models/helmet_yolov8n.pt. Validates the model loads correctly
and reports expected classes. Uses only stdlib (no pip install needed).

Usage:
    python download_helmet_model.py
"""

import os, sys, logging, urllib.request, shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

REPO_ID = "iam-tsr/yolov8n-helmet-detection"
HF_FILENAME = "best.pt"
MODEL_DIR = Path(__file__).parent / "models"
OUTPUT_PATH = MODEL_DIR / "helmet_yolov8n.pt"

EXPECTED_CLASSES = {0: 'With Helmet', 1: 'Without Helmet'}
EXPECTED_CLASS_COUNT = 2


def _progress_hook(block_count, block_size, total_size):
    if total_size > 0:
        downloaded = block_count * block_size
        pct = min(downloaded / total_size * 100, 100)
        sys.stdout.write(f"\r  Progress: {pct:.0f}% ({downloaded // 1024} KB / {total_size // 1024} KB)")
        sys.stdout.flush()


def download():
    """Download model from Hugging Face Hub to OUTPUT_PATH."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    url = f"https://huggingface.co/{REPO_ID}/resolve/main/{HF_FILENAME}"
    logger.info(f"Downloading from {url} ...")

    try:
        urllib.request.urlretrieve(url, OUTPUT_PATH, _progress_hook)
    except Exception as e:
        logger.error(f"Download failed: {e}")
        sys.exit(1)
    print()
    logger.info(f"Saved to {OUTPUT_PATH}")
    return str(OUTPUT_PATH)


def validate_model(path):
    """Load the model with Ultralytics YOLO and check classes."""
    try:
        from ultralytics import YOLO
    except ImportError:
        logger.error("ultralytics not installed. Run: pip install ultralytics")
        return False

    logger.info("Validating model...")
    try:
        model = YOLO(path)
    except Exception as e:
        logger.error(f"Failed to load model with YOLO: {e}")
        return False

    names = model.names
    n_classes = len(names)
    logger.info(f"  Classes ({n_classes}): {names}")

    if n_classes != EXPECTED_CLASS_COUNT:
        logger.warning(f"Expected {EXPECTED_CLASS_COUNT} classes, got {n_classes}")
    if names != EXPECTED_CLASSES:
        logger.warning(f"Class names differ from expected: got {names}")

    import numpy as np
    dummy = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    try:
        results = model(dummy, conf=0.25, iou=0.45, verbose=False)
        logger.info(f"  Inference test: OK ({len(results[0].boxes)} detections on random noise)")
    except Exception as e:
        logger.error(f"Inference test failed: {e}")
        return False

    logger.info("Model validation PASSED")
    return True


def main():
    final_path = download()

    if not os.path.exists(final_path):
        logger.error("Download failed: file not found")
        sys.exit(1)

    size_mb = os.path.getsize(final_path) / (1024 * 1024)
    logger.info(f"File size: {size_mb:.1f} MB")

    if not validate_model(final_path):
        logger.error("Model validation FAILED")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f" Model ready: {OUTPUT_PATH}")
    print(f" Size: {size_mb:.1f} MB")
    print(f" Source: {REPO_ID}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
