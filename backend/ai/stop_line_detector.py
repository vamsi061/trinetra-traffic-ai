import cv2
import numpy as np
import config


def detect_stop_lines(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    h, w = image.shape[:2]

    roi_y1 = int(h * 0.50)
    roi = edges[roi_y1:int(h * 0.85), :]

    if roi.shape[0] < 20:
        return [], gray, edges

    lines = cv2.HoughLinesP(
        roi, rho=1, theta=np.pi / 180,
        threshold=50, minLineLength=int(w * 0.45), maxLineGap=20
    )

    if lines is None:
        return [], gray, edges

    stop_lines = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if angle > 10 and angle < 170:
            continue

        line_len = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if line_len < w * 0.45:
            continue

        line_cx = (x1 + x2) / 2
        line_cy = roi_y1 + (y1 + y2) / 2

        if line_cx < w * 0.30 or line_cx > w * 0.70:
            continue
        if line_cy > h * 0.85:
            continue

        contrast = _measure_line_contrast(gray, x1, y1 + roi_y1, x2, y2 + roi_y1)
        visibility = _measure_line_visibility(edges, x1, y1 + roi_y1, x2, y2 + roi_y1, roi_y1)

        stop_lines.append({
            'x1': x1, 'y1': y1 + roi_y1,
            'x2': x2, 'y2': y2 + roi_y1,
            'cx': line_cx, 'cy': line_cy,
            'length': line_len,
            'contrast': contrast,
            'visibility': visibility,
        })

    return stop_lines, gray, edges


def _measure_line_contrast(gray, x1, y1, x2, y2):
    """Measure pixel intensity variation perpendicular to the line."""
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    h, w = gray.shape
    x_start = max(0, cx - 15)
    x_end = min(w, cx + 15)
    y_start = max(0, cy - 3)
    y_end = min(h, cy + 3)
    strip = gray[y_start:y_end, x_start:x_end]
    if strip.size < 10:
        return 0.3
    contrast = float(np.std(strip)) / 255.0
    return min(1.0, contrast * 3.0)


def _measure_line_visibility(edges, x1, y1, x2, y2, roi_offset):
    """What fraction of the line pixels are on edge?."""
    line_mask = np.zeros_like(edges, dtype=np.uint8)
    cv2.line(line_mask, (x1, y1), (x2, y2), 255, 3)
    edge_pixels = cv2.countNonZero(cv2.bitwise_and(edges, line_mask))
    line_pixels = cv2.countNonZero(line_mask)
    if line_pixels == 0:
        return 0.3
    return min(1.0, edge_pixels / max(line_pixels, 1))


def assess_image_quality_for_stop_line(image):
    """Return 0.0–1.0 quality score."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    sharpness = min(1.0, laplacian_var / 500.0)
    brightness = float(np.mean(gray)) / 255.0
    return max(0.3, min(1.0, 0.6 * sharpness + 0.4 * brightness))


def compute_vehicle_overlap(vehicle_bbox, stop_line, image):
    """How clearly the vehicle is past the stop line (0.0–1.0)."""
    _, y1, _, y2 = vehicle_bbox
    veh_center_y = (y1 + y2) / 2
    veh_bottom = y2
    h = image.shape[0]

    gap = veh_bottom - stop_line['cy']
    max_gap = h * 0.30
    gap_ratio = max(0.0, min(1.0, gap / max_gap))

    center_past = max(0.0, (veh_center_y - stop_line['cy']) / (h * 0.20))
    center_past = min(1.0, center_past)

    return 0.6 * gap_ratio + 0.4 * center_past


def compute_vehicle_size_confidence(vehicle_bbox, image):
    """Larger vehicles closer to camera get higher size confidence."""
    h, w = image.shape[:2]
    _, y1, _, y2 = vehicle_bbox
    veh_h = y2 - y1
    veh_w = vehicle_bbox[2] - vehicle_bbox[0]
    veh_area = veh_h * veh_w
    img_area = h * w
    area_ratio = veh_area / img_area
    return min(1.0, area_ratio / 0.10)


def check_stop_line_violation(detections, image):
    violations = []
    h, w = image.shape[:2]

    stop_lines, gray, edges = detect_stop_lines(image)
    if not stop_lines:
        return violations

    vehicles = [d for d in detections if d.get('class_id') in config.VEHICLE_CLASSES]
    if not vehicles:
        return violations

    stop_line = max(stop_lines, key=lambda s: s['length'])

    scene_quality = assess_image_quality_for_stop_line(image)

    max_possible_len = np.sqrt(w ** 2 + (h * 0.35) ** 2)
    line_length_score = min(1.0, stop_line['length'] / max_possible_len)
    line_contrast = stop_line.get('contrast', 0.5)
    line_visibility = stop_line.get('visibility', 0.5)

    for veh in vehicles:
        veh_h = veh['bbox'][3] - veh['bbox'][1]
        veh_w = veh['bbox'][2] - veh['bbox'][0]
        veh_area = veh_h * veh_w
        img_area = h * w

        if veh_area / img_area < 0.02:
            continue
        if veh['bbox'][3] < h * 0.45:
            continue

        if not _is_vehicle_past_stop_line(veh['bbox'], stop_line, image):
            continue

        vehicle_overlap = compute_vehicle_overlap(veh['bbox'], stop_line, image)
        vehicle_size = compute_vehicle_size_confidence(veh['bbox'], image)

        confidence = (
            0.20 * line_length_score +
            0.20 * line_contrast +
            0.15 * line_visibility +
            0.25 * vehicle_overlap +
            0.20 * scene_quality
        )
        confidence = max(0.30, min(0.98, confidence))

        conf_band = 'high' if confidence >= 0.80 else ('medium' if confidence >= 0.60 else 'low')

        vtype = config.VEHICLE_CLASSES.get(veh['class_id'], 'vehicle')
        violations.append({
            'violation_type': 'STOP_LINE_VIOLATION',
            'display_type': 'Stop Line Violation',
            'confidence': round(confidence, 3),
            'confidence_band': conf_band,
            'detection_source': 'Hough Transform + Geometric Validation',
            'vehicle_bbox': veh['bbox'],
            'vehicle_type': vtype,
            'severity_score': config.RISK_SCORES.get('STOP_LINE_VIOLATION', 60),
            'stop_line_y': int(stop_line['cy']),
            'description': f'{veh.get("instance_id", vtype)} crossed stop line',
            'involved_objects': [veh.get('instance_id', vtype)],
            'needs_review': confidence < 0.70,
            'stop_line_diagnostics': {
                'line_length_score': round(line_length_score, 3),
                'line_contrast': round(line_contrast, 3),
                'line_visibility_score': round(line_visibility, 3),
                'vehicle_overlap_score': round(vehicle_overlap, 3),
                'scene_quality': round(scene_quality, 3),
            },
        })

    return violations


def _is_vehicle_past_stop_line(vehicle_bbox, stop_line, image):
    _, y1, _, y2 = vehicle_bbox
    veh_center_y = (y1 + y2) / 2
    veh_bottom = y2
    return veh_bottom > stop_line['cy'] and (veh_center_y - stop_line['cy']) > image.shape[0] * 0.03
