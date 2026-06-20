import cv2
import numpy as np


def assess_quality(image):
    """Assess image quality metrics.

    Returns:
        dict with: score (Excellent/Good/Fair/Poor),
                   issues (list of detected problems),
                   expected_accuracy_impact (str)
    """
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    issues = []

    # Brightness check (low light / glare)
    mean_brightness = gray.mean()
    if mean_brightness < 60:
        issues.append('Low Light')
    elif mean_brightness > 220:
        issues.append('Glare')
    elif mean_brightness < 100:
        issues.append('Dim')

    # Blur detection using Laplacian variance
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 50:
        issues.append('Blur')
    elif laplacian_var < 100:
        issues.append('Slight Blur')

    # Contrast check
    contrast = gray.std()
    if contrast < 30:
        issues.append('Low Contrast')

    # Fog/haze detection — require BOTH desaturation AND other quality issue
    # to avoid false positives on clear daylight road scenes (gray roads are naturally desaturated)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1].mean()
    if saturation < 25 and mean_brightness > 100 and (laplacian_var < 80 or contrast < 35):
        issues.append('Fog/Haze')

    # Shadow detection (large dark regions)
    dark_mask = gray < 50
    dark_ratio = cv2.countNonZero(dark_mask.astype(np.uint8)) / (h * w)
    if dark_ratio > 0.3:
        issues.append('Shadow')
    elif dark_ratio > 0.15:
        issues.append('Partial Shadow')

    # Determine overall score
    if len(issues) == 0:
        score = 'Excellent'
        impact = 'Minimal'
    elif len(issues) <= 1:
        score = 'Good'
        impact = 'Low'
    elif len(issues) <= 2:
        score = 'Fair'
        impact = 'Moderate'
    else:
        score = 'Poor'
        impact = 'High'

    return {
        'score': score,
        'issues': issues,
        'brightness': round(float(mean_brightness), 1),
        'sharpness': round(float(laplacian_var), 1),
        'contrast': round(float(contrast), 1),
        'expected_accuracy_impact': impact,
    }
