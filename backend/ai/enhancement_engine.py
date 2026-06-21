"""Adaptive Enhancement Engine for TRINETRA AI.

Applies only the enhancement steps needed based on image quality assessment.
Includes fail-safe: reverts to original if enhancement degrades quality.
"""
import cv2
import numpy as np
import logging
from copy import deepcopy

from ai.image_quality import analyze_quality

logger = logging.getLogger(__name__)


def _gamma_correction(image, gamma=1.5):
    inv = 1.0 / gamma
    table = np.array([(i / 255.0) ** inv * 255 for i in range(256)], dtype=np.uint8)
    return cv2.LUT(image, table)


def _clahe(image, clip=3.0, grid=(8, 8)):
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=grid)
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


def _adaptive_brightness(image, target_brightness=0.45):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    current = np.mean(gray) / 255.0
    if current < 0.01:
        return image
    beta = (target_brightness - current) * 255.0
    return cv2.convertScaleAbs(image, alpha=1.0, beta=beta)


def _denoise(image, h=10):
    return cv2.fastNlMeansDenoisingColored(image, None, h, h, 7, 21)


def _unsharp_mask(image, strength=1.5, radius=3):
    blurred = cv2.GaussianBlur(image, (0, 0), radius)
    return cv2.addWeighted(image, strength, blurred, 1.0 - strength, 0)


def _dehaze_dcp(image):
    """Dark Channel Prior dehazing."""
    img = image.astype(np.float64) / 255.0
    h, w = img.shape[:2]
    patch = 15
    dark = np.min(img, axis=2)

    # Erode dark channel
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (patch, patch))
    dark = cv2.erode(dark, kernel)

    # Estimate atmospheric light
    flat = dark.ravel()
    num_pixels = flat.size
    top_k = int(max(num_pixels * 0.001, 1))
    indices = np.argpartition(flat, -top_k)[-top_k:]
    brightest = np.unravel_index(indices, dark.shape)
    atmospheric = np.max(img[brightest], axis=0)

    # Transmission map
    transmission = 1.0 - 0.95 * dark

    # Refine transmission
    transmission = cv2.boxFilter(transmission, -1, (patch, patch))
    transmission = np.clip(transmission, 0.1, 1.0)

    # Recover
    recovered = np.zeros_like(img)
    for c in range(3):
        recovered[:, :, c] = (img[:, :, c] - atmospheric[c]) / transmission + atmospheric[c]

    recovered = np.clip(recovered * 255.0, 0, 255).astype(np.uint8)
    return recovered


def _super_resolve(image, scale=2):
    """Simple edge-preserving upscale using Lanczos interpolation."""
    h, w = image.shape[:2]
    new_size = (w * scale, h * scale)
    return cv2.resize(image, new_size, interpolation=cv2.INTER_LANCZOS4)


class AdaptiveEnhancementEngine:
    """Applies targeted enhancements based on quality analysis."""

    def __init__(self):
        self.last_quality_before = None
        self.last_quality_after = None
        self.last_enhancements = []

    def enhance(self, image):
        """Analyze quality and apply only needed enhancements.
        
        Returns:
            (enhanced_image, quality_before, quality_after, enhancements_applied)
        """
        if image is None:
            return None, None, None, []

        q_before = analyze_quality(image)
        self.last_quality_before = q_before
        enhanced = image.copy()
        applied = []

        # 1. Low Light Enhancement
        if q_before['brightness'] < 0.30:
            logger.info(f"Applying low-light enhancement (brightness={q_before['brightness']:.2f})")
            enhanced = _gamma_correction(enhanced, gamma=1.8)
            enhanced = _adaptive_brightness(enhanced, target_brightness=0.40)
            enhanced = _clahe(enhanced, clip=2.0, grid=(8, 8))
            applied.append('Gamma Correction')
            applied.append('Adaptive Brightness')
            applied.append('CLAHE')

        # 2. Contrast Enhancement
        if q_before['contrast'] < 0.20:
            logger.info(f"Applying contrast enhancement (contrast={q_before['contrast']:.2f})")
            enhanced = _clahe(enhanced, clip=3.0, grid=(8, 8))
            applied.append('CLAHE')

        # 3. Denoising
        if q_before['noise'] > 0.02:
            strength = min(int(q_before['noise'] * 500), 15)
            logger.info(f"Applying denoising (noise={q_before['noise']:.3f}, strength={strength})")
            enhanced = _denoise(enhanced, h=strength)
            applied.append('Denoising')

        # 4. Deblurring / Sharpening
        if q_before['sharpness'] < 0.15:
            logger.info(f"Applying sharpening (sharpness={q_before['sharpness']:.3f})")
            strength = 2.0 if q_before['sharpness'] < 0.08 else 1.5
            enhanced = _unsharp_mask(enhanced, strength=strength)
            applied.append('Sharpening')

        # 5. Dehazing
        if q_before.get('haze', 0) > 0.65:
            logger.info(f"Applying dehazing (haze={q_before['haze']:.2f})")
            try:
                enhanced = _dehaze_dcp(enhanced)
                applied.append('Dehazing')
            except Exception as e:
                logger.warning(f"Dehazing failed: {e}")

        # 6. Super-resolution for low-res images
        h, w = image.shape[:2]
        if (h < 300 or w < 300) and q_before.get('resolution_score', 1) < 0.5:
            logger.info(f"Applying super-resolution ({w}x{h} -> {w*2}x{h*2})")
            enhanced = _super_resolve(enhanced, scale=2)
            applied.append('Super Resolution')

        # 7. Fallback: mild general enhancement if nothing else applied
        if not applied:
            enhanced = _clahe(enhanced, clip=2.0, grid=(8, 8))
            enhanced = _unsharp_mask(enhanced, strength=1.2)
            applied.append('CLAHE')
            applied.append('Light Sharpening')

        # FAIL-SAFE: Check if enhancement degraded quality
        q_after = analyze_quality(enhanced)
        self.last_quality_after = q_after
        self.last_enhancements = applied

        if q_after['quality_score'] < q_before['quality_score'] * 0.85:
            logger.warning(
                f"Enhancement degraded quality ({q_before['quality_score']:.2f} -> {q_after['quality_score']:.2f}). "
                "Reverting to original."
            )
            self.last_quality_after = q_before
            self.last_enhancements = ['Reverted to original (enhancement degraded quality)']
            return image, q_before, q_before, ['Reverted to original']

        return enhanced, q_before, q_after, applied

    def get_report(self):
        return {
            'quality_before': self.last_quality_before,
            'quality_after': self.last_quality_after,
            'enhancements_applied': self.last_enhancements,
        }
