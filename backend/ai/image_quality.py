"""Image Quality Assessment for TRINETRA AI.

Analyzes image quality metrics before enhancement to guide adaptive enhancement.
"""
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


def _estimate_noise(image_gray):
    """Estimate noise level using median of local variance."""
    h, w = image_gray.shape
    blocks = 8
    bh, bw = h // blocks, w // blocks
    variances = []
    for i in range(blocks):
        for j in range(blocks):
            block = image_gray[i*bh:(i+1)*bh, j*bw:(j+1)*bw]
            if block.size > 0:
                variances.append(np.var(block))
    if not variances:
        return 0.0
    noise = np.median(variances) / 255.0
    return min(noise, 1.0)


def _estimate_blur(image_gray):
    """Estimate blur using Laplacian variance (lower = more blurred)."""
    lap = cv2.Laplacian(image_gray, cv2.CV_64F)
    lap_var = lap.var()
    # Normalize: typical sharp image ~100-500, blurred < 50
    blur_score = min(lap_var / 1000.0, 1.0)
    return blur_score  # higher = sharper


def _estimate_brightness(image):
    """Estimate overall brightness (0=dark, 1=overexposed)."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mean_brightness = np.mean(gray) / 255.0
    return mean_brightness


def _estimate_contrast(image_gray):
    """Estimate contrast using std of pixel intensities."""
    return min(np.std(image_gray) / 128.0, 1.0)


def _estimate_visibility(image, image_gray):
    """Estimate visibility from edge density and mid-tone distribution."""
    edges = cv2.Canny(image_gray, 50, 150)
    edge_density = np.count_nonzero(edges) / edges.size
    # Mid-tone ratio (pixels in 40-200 range)
    mid = np.sum((image_gray > 40) & (image_gray < 200)) / image_gray.size
    visibility = (edge_density * 0.6 + mid * 0.4)
    return min(visibility * 2.0, 1.0)


def _detect_haze(image_gray):
    """Detect haze by checking low-frequency contrast suppression."""
    h, w = image_gray.shape
    top = image_gray[:h//3, :]
    bot = image_gray[2*h//3:, :]
    if top.size == 0 or bot.size == 0:
        return 0.0
    top_mean = np.mean(top)
    bot_mean = np.mean(bot)
    # Hazy images have flat intensity across distance
    diff = abs(float(top_mean) - float(bot_mean)) / 255.0
    haze_score = 1.0 - min(diff * 5.0, 1.0)
    return haze_score


def _detect_overexposure(image_gray):
    """Fraction of pixels saturated (>250)."""
    return float(np.sum(image_gray > 250)) / image_gray.size


def _detect_underexposure(image_gray):
    """Fraction of pixels near black (<10)."""
    return float(np.sum(image_gray < 10)) / image_gray.size


def _detect_low_resolution(image):
    """Check if image resolution is below threshold."""
    h, w = image.shape[:2]
    if h < 200 or w < 200:
        return 1.0
    if h < 400 or w < 400:
        return 0.5
    return 0.0


def analyze_quality(image):
    """Full image quality analysis.

    Args:
        image: BGR numpy array

    Returns:
        dict with quality scores, issues, and overall rating
    """
    if image is None:
        return {
            'quality': 'Poor',
            'brightness': 0.0, 'contrast': 0.0, 'sharpness': 0.0,
            'noise': 0.0, 'visibility': 0.0, 'blur_score': 0.0,
            'issues': ['No image data'],
            'resolution_score': 0.0,
        }

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = image.shape[:2]

    brightness = _estimate_brightness(image)
    contrast = _estimate_contrast(gray)
    sharpness = _estimate_blur(gray)  # higher = sharper
    noise = _estimate_noise(gray)
    visibility = _estimate_visibility(image, gray)
    haze = _detect_haze(gray)
    overexp = _detect_overexposure(gray)
    underexp = _detect_underexposure(gray)
    low_res = _detect_low_resolution(image)

    issues = []
    if brightness < 0.25:
        issues.append('Low Light')
    elif brightness > 0.85:
        issues.append('Overexposed')

    if sharpness < 0.05:
        issues.append('Motion Blur')
    elif sharpness < 0.15:
        issues.append('Soft Focus')

    if noise > 0.02:
        issues.append('Noise')

    if haze > 0.65:
        issues.append('Haze/Fog')

    if overexp > 0.1:
        issues.append('Overexposure')

    if underexp > 0.1:
        issues.append('Underexposure')

    if low_res > 0.5:
        issues.append('Low Resolution')

    if contrast < 0.15:
        issues.append('Low Contrast')

    # Composite quality score (0-1)
    quality_score = (
        0.25 * brightness +
        0.20 * contrast +
        0.20 * sharpness +
        0.20 * visibility +
        0.15 * (1.0 - noise)
    )
    quality_score = max(0.0, min(1.0, quality_score))

    if quality_score >= 0.75:
        quality_label = 'Excellent'
    elif quality_score >= 0.55:
        quality_label = 'Good'
    elif quality_score >= 0.35:
        quality_label = 'Fair'
    else:
        quality_label = 'Poor'

    return {
        'quality': quality_label,
        'quality_score': round(quality_score, 3),
        'brightness': round(brightness, 3),
        'contrast': round(contrast, 3),
        'sharpness': round(sharpness, 3),
        'blur_score': round(1.0 - sharpness, 3),
        'noise': round(noise, 3),
        'visibility': round(visibility, 3),
        'haze': round(haze, 3),
        'overexposure': round(overexp, 3),
        'underexposure': round(underexp, 3),
        'resolution_score': round(1.0 - low_res, 3),
        'issues': issues,
        'resolution': f'{w}x{h}',
    }


class ImageQualityAnalyzer:
    """Singleton analyzer that caches per-image quality assessments."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache = {}
        return cls._instance

    def analyze(self, image, image_id=None):
        key = image_id or id(image)
        if key in self._cache:
            return self._cache[key]
        result = analyze_quality(image)
        self._cache[key] = result
        return result

    def clear_cache(self):
        self._cache = {}
