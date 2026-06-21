"""License Plate Enhancement Service for TRINETRA AI.

Dedicated plate crop, enhance, and OCR pipeline with before/after comparison.
"""
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


def _sharpen(image):
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    return cv2.filter2D(image, -1, kernel)


def _clahe_plate(gray, clip=2.0, grid=(4, 4)):
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=grid)
    return clahe.apply(gray)


def _binarize(gray):
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def _denoise_plate(gray):
    return cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)


def _upscale(gray, scale=2):
    h, w = gray.shape
    return cv2.resize(gray, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)


def enhance_plate_region(plate_bbox, source_image):
    """Crop, enhance, and return plate region.

    Args:
        plate_bbox: [x1, y1, x2, y2] in source image coords
        source_image: full BGR image

    Returns:
        dict with original_plate, enhanced_plate (both BGR), steps applied
    """
    x1, y1, x2, y2 = [int(v) for v in plate_bbox]
    h, w = source_image.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)

    if x2 <= x1 or y2 <= y1:
        return None

    plate_region = source_image[y1:y2, x1:x2]
    if plate_region.size == 0:
        return None

    gray = cv2.cvtColor(plate_region, cv2.COLOR_BGR2GRAY)
    steps = []

    enhanced = gray.copy()

    # 1. Denoise
    if gray.size > 100:
        enhanced = _denoise_plate(enhanced)
        steps.append('Denoising')

    # 2. CLAHE
    enhanced = _clahe_plate(enhanced)
    steps.append('CLAHE')

    # 3. Sharpen
    enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    enhanced_bgr = _sharpen(enhanced_bgr)
    enhanced = cv2.cvtColor(enhanced_bgr, cv2.COLOR_BGR2GRAY)
    steps.append('Sharpening')

    # 4. Upscale if plate is small
    ph, pw = gray.shape
    if ph < 30 or pw < 80:
        scale = max(2, 80 // pw, 30 // ph)
        enhanced = _upscale(enhanced, scale=scale)
        steps.append(f'Upscale {scale}x')

    # 5. Binarize for OCR
    binary = _binarize(enhanced)
    steps.append('Binarization')

    return {
        'original_plate_bgr': plate_region,
        'enhanced_plate_gray': enhanced,
        'binary_plate': binary,
        'steps': steps,
        'bbox': [x1, y1, x2, y2],
    }
