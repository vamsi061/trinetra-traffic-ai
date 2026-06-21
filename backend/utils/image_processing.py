"""TRINETRA AI — Production Image Enhancement Pipeline.

Adaptive enhancement using ImageQualityAnalyzer and AdaptiveEnhancementEngine.
Fallback: basic CLAHE if adaptive engine unavailable.
"""
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

_enhancement_engine = None
_quality_analyzer = None


def _get_engine():
    global _enhancement_engine
    if _enhancement_engine is None:
        try:
            from ai.enhancement_engine import AdaptiveEnhancementEngine
            _enhancement_engine = AdaptiveEnhancementEngine()
        except Exception as e:
            logger.warning(f"Adaptive enhancement engine unavailable: {e}")
    return _enhancement_engine


def _get_analyzer():
    global _quality_analyzer
    if _quality_analyzer is None:
        try:
            from ai.image_quality import ImageQualityAnalyzer
            _quality_analyzer = ImageQualityAnalyzer()
        except Exception as e:
            logger.warning(f"Image quality analyzer unavailable: {e}")
    return _quality_analyzer


def enhance_image(image):
    """Enhanced image with adaptive pipeline. Falls back to basic CLAHE."""
    if image is None:
        return None

    engine = _get_engine()
    if engine is not None:
        try:
            enhanced, q_before, q_after, applied = engine.enhance(image)
            logger.debug(f"Enhancement: {q_before['quality']} -> {q_after['quality']}, steps={applied}")
            return enhanced
        except Exception as e:
            logger.warning(f"Adaptive enhancement failed: {e}, using fallback")

    # Fallback: basic CLAHE
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    enhanced = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
    return enhanced


def analyze_image_quality(image):
    """Get quality assessment dict for an image."""
    analyzer = _get_analyzer()
    if analyzer is None:
        return {'quality': 'Unknown', 'issues': []}
    return analyzer.analyze(image)


def get_enhancement_report():
    """Get the latest enhancement report from the engine."""
    engine = _get_engine()
    if engine is None:
        return {}
    return engine.get_report()


def preprocess_for_ocr(region):
    """Legacy OCR preprocessing."""
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    return thresh


def create_comparison(image_before, image_after, max_width=1200):
    """Side-by-side before/after comparison image.

    Args:
        image_before: original BGR image
        image_after: enhanced BGR image
        max_width: max total width

    Returns:
        side-by-side BGR image with labels, or just enhanced if something fails
    """
    try:
        h1, w1 = image_before.shape[:2]
        h2, w2 = image_after.shape[:2]

        target_h = max(h1, h2)
        scale_before = target_h / h1 if h1 > 0 else 1
        scale_after = target_h / h2 if h2 > 0 else 1

        before_resized = cv2.resize(image_before, (int(w1 * scale_before), target_h))
        after_resized = cv2.resize(image_after, (int(w2 * scale_after), target_h))

        gap = 4
        total_w = before_resized.shape[1] + gap + after_resized.shape[1]

        if total_w > max_width:
            scale = max_width / total_w
            before_resized = cv2.resize(before_resized, (int(before_resized.shape[1] * scale), int(target_h * scale)))
            after_resized = cv2.resize(after_resized, (int(after_resized.shape[1] * scale), int(target_h * scale)))
            target_h = before_resized.shape[0]
            total_w = before_resized.shape[1] + gap + after_resized.shape[1]

        comparison = np.zeros((target_h + 40, total_w, 3), dtype=np.uint8)
        comparison[40:40 + target_h, :before_resized.shape[1]] = before_resized
        comparison[40:40 + target_h, before_resized.shape[1] + gap:before_resized.shape[1] + gap + after_resized.shape[1]] = after_resized

        # Draw separator line
        sep_x = before_resized.shape[1] + gap // 2
        cv2.line(comparison, (sep_x, 40), (sep_x, 40 + target_h), (255, 255, 255), 2)

        # Labels
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(comparison, 'Original', (10, 28), font, 0.7, (200, 200, 200), 2)
        cv2.putText(comparison, 'Enhanced', (before_resized.shape[1] + gap + 10, 28), font, 0.7, (200, 200, 200), 2)

        return comparison
    except Exception as e:
        logger.warning(f"Comparison generation failed: {e}")
        return image_after if image_after is not None else image_before


# Keep legacy functions for backward compatibility
def enhance_brightness(image, alpha=1.2, beta=30):
    return cv2.convertScaleAbs(image, alpha=alpha, beta=beta)


def enhance_contrast(image):
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


def reduce_noise(image, strength=10):
    return cv2.fastNlMeansDenoisingColored(image, None, strength, strength, 7, 21)
