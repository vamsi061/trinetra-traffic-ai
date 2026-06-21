"""Motion validation for traffic violations.

Determines whether a detected vehicle is moving or stationary
using temporal and spatial cues from a single image.
"""

import logging
import cv2
import numpy as np
import config

logger = logging.getLogger(__name__)

# Minimum edge/line density below which a vehicle is likely static
EDGE_DENSITY_STATIC_THRESHOLD = 0.06
MOTION_BLUR_THRESHOLD = 3.0


def _estimate_motion_blur(vehicle_roi):
    """Estimate motion blur in vehicle region via Laplacian variance.

    Higher variance = sharper image = vehicle likely stationary.
    Low variance suggests motion blur (moving vehicle).

    Returns:
        float: Laplacian variance (higher = sharper = more likely stationary)
    """
    if vehicle_roi.size == 0 or vehicle_roi.shape[0] < 10 or vehicle_roi.shape[1] < 10:
        return 0.0
    gray = cv2.cvtColor(vehicle_roi, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def _check_optical_flow_artifacts(vehicle_roi):
    """Check for motion artifacts around vehicle edges.

    Moving vehicles often show directional edge smearing.
    Returns a score 0.0 (no motion) to 1.0 (clear motion).
    """
    if vehicle_roi.size == 0 or vehicle_roi.shape[0] < 10 or vehicle_roi.shape[1] < 10:
        return 0.0
    gray = cv2.cvtColor(vehicle_roi, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 30, 100)
    if cv2.countNonZero(edges) < 10:
        return 0.0
    # Compute horizontal vs vertical edge ratio
    # Moving vehicles often have stronger horizontal motion streaks
    sobel_h = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_v = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    mag_h = np.abs(sobel_h).mean()
    mag_v = np.abs(sobel_v).mean()
    if mag_v < 1.0:
        return 0.0
    ratio = mag_h / mag_v
    # ratio > 1.5 suggests horizontal motion
    return min(1.0, max(0.0, (ratio - 0.8) / 1.5))


def _vehicle_has_mounting_context(vehicle_bbox, detections, image_shape):
    """Check if a person is mounted on this vehicle (rider in position).
    
    A mounted rider suggests the vehicle is in use and could be moving.
    """
    h, _ = image_shape[:2]
    vx1, vy1, vx2, vy2 = vehicle_bbox
    v_cx = (vx1 + vx2) / 2
    v_cy = (vy1 + vy2) / 2
    v_w = vx2 - vx1

    persons = [d for d in detections if d['class_id'] == config.PERSON_CLASS_ID]
    for p in persons:
        px1, py1, px2, py2 = p['bbox']
        p_cx = (px1 + px2) / 2
        p_cy = (py1 + py2) / 2
        # Person above vehicle center (sitting position)
        if p_cy < v_cy and abs(p_cx - v_cx) < v_w * 0.8:
            return True
    return False


def validate_motion(vehicle_bbox, image, detections):
    """Validate whether a vehicle appears to be in motion.

    Returns:
        dict with:
            is_moving: bool or None if uncertain
            motion_confidence: float 0-1
            evidence: list of motion evidence clues
    """
    h, w = image.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in vehicle_bbox]
    # Clamp to image bounds
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    roi = image[y1:y2, x1:x2]

    evidence = []
    motion_score = 0.0
    total_weight = 0.0

    # 1. Motion blur
    blur = _estimate_motion_blur(roi)
    if blur > 0:
        is_blurry = blur < MOTION_BLUR_THRESHOLD
        evidence.append(f'Laplacian variance={blur:.1f} ({"blurry=moving" if is_blurry else "sharp=stationary"})')
        if is_blurry:
            motion_score += 0.35
        else:
            motion_score += 0.0  # sharp → stationary evidence, handled below
        total_weight += 0.35

    # 2. Motion artifacts (horizontal edge smear)
    artifact = _check_optical_flow_artifacts(roi)
    if artifact > 0.3:
        evidence.append(f'motion artifacts={artifact:.2f}')
        motion_score += 0.25 * artifact
        total_weight += 0.25

    # 3. Mounted rider context
    has_rider = _vehicle_has_mounting_context(vehicle_bbox, detections, image.shape)
    if has_rider:
        evidence.append('mounted rider present')
        motion_score += 0.20
        total_weight += 0.20

    # 4. Vehicle position in travel lane (center region)
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    in_lane = (cx > w * 0.15 and cx < w * 0.85 and cy > h * 0.15 and cy < h * 0.85)
    if in_lane:
        evidence.append('vehicle in travel lane')
        motion_score += 0.20
        total_weight += 0.20

    if total_weight == 0:
        return {'is_moving': None, 'motion_confidence': 0.0, 'evidence': ['insufficient motion data']}

    normalized = motion_score / total_weight

    # Sharp image + no artifacts + in lane shoulder = stationary evidence
    sharp_and_centered = blur > MOTION_BLUR_THRESHOLD * 2 and artifact < 0.2 and in_lane
    if sharp_and_centered:
        normalized = max(0, normalized - 0.3)  # reduce motion score

    is_moving = normalized > 0.40
    if abs(normalized - 0.40) < 0.15:
        is_moving = None  # uncertain

    return {
        'is_moving': is_moving,
        'motion_confidence': round(normalized, 3),
        'evidence': evidence,
    }
