"""Confidence Fusion Service for TRINETRA AI v2.

Combines confidence scores from multiple models into a single fused score:

    YOLO Confidence
    Helmet Model Confidence
    OCR Confidence
    Reasoning Confidence

Fusion uses weighted averaging with dynamic weights based on availability
and scene conditions (crowding, lighting, etc.).
"""
import logging

logger = logging.getLogger(__name__)

# Base weights for each confidence source
WEIGHTS = {
    'yolo': 1.0,
    'helmet_model': 0.9,
    'ocr': 0.7,
    'reasoning': 0.6,
}

# Crowded scene penalty factors
CROWDED_PENALTY = {
    'yolo': 0.9,
    'helmet_model': 0.8,
    'ocr': 0.9,
    'reasoning': 0.7,
}


def fuse(confidences, crowded=False):
    """Fuse multiple confidence sources into a single score.

    Args:
        confidences: dict of source_name -> confidence (0-1).
            Expected keys: 'yolo', 'helmet_model', 'ocr', 'reasoning'
        crowded: bool — if True, apply crowding penalties

    Returns:
        dict with:
            fused: float (0-1)
            sources_used: list of source names
            weights_used: dict of source_name -> effective_weight
    """
    available = {k: v for k, v in confidences.items() if v is not None}
    if not available:
        return {
            'fused': 0.5,
            'sources_used': [],
            'weights_used': {},
        }

    weights_used = {}
    weighted_sum = 0.0
    total_weight = 0.0

    for source, conf in available.items():
        weight = WEIGHTS.get(source, 0.5)
        if crowded:
            weight *= CROWDED_PENALTY.get(source, 0.85)
        weights_used[source] = round(weight, 3)
        weighted_sum += weight * conf
        total_weight += weight

    fused = weighted_sum / total_weight if total_weight > 0 else 0.5
    fused = max(0.0, min(1.0, fused))

    return {
        'fused': round(fused, 3),
        'sources_used': list(available.keys()),
        'weights_used': weights_used,
    }


def fuse_violation(violation_conf, yolo_conf=None, helmet_conf=None,
                   ocr_conf=None, reasoning_conf=None, crowded=False):
    """Convenience: fuse confidence for a single violation."""
    return fuse({
        'yolo': yolo_conf,
        'helmet_model': helmet_conf,
        'ocr': ocr_conf,
        'reasoning': reasoning_conf,
    }, crowded=crowded)


def fuse_detection(yolo_conf, reasoning_conf=None, crowded=False):
    """Fuse confidence for a detection."""
    return fuse({
        'yolo': yolo_conf,
        'reasoning': reasoning_conf,
    }, crowded=crowded)


def fuse_ocr(easyocr_conf, paddleocr_conf=None, reasoning_conf=None):
    """Fuse confidence for OCR result."""
    return fuse({
        'ocr': easyocr_conf if easyocr_conf else paddleocr_conf,
        'reasoning': reasoning_conf,
        'easyocr': easyocr_conf,
        'paddleocr': paddleocr_conf,
    }, crowded=False)
