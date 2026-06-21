import cv2
import numpy as np
import config


def detect_stop_lines(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    h, w = image.shape[:2]

    # Focus on lower portion where stop lines are visible
    roi_y1 = int(h * 0.4)
    roi = edges[roi_y1:, :]

    lines = cv2.HoughLinesP(
        roi, rho=1, theta=np.pi / 180,
        threshold=30, minLineLength=int(w * 0.2), maxLineGap=20
    )

    if lines is None:
        return []

    stop_lines = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        # Horizontal-ish lines
        angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if angle < 20 or angle > 160:
            line_cx = (x1 + x2) / 2
            line_cy = roi_y1 + (y1 + y2) / 2
            stop_lines.append({
                'x1': x1, 'y1': y1 + roi_y1,
                'x2': x2, 'y2': y2 + roi_y1,
                'cx': line_cx, 'cy': line_cy,
                'length': np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2),
            })

    return stop_lines


def is_vehicle_past_stop_line(vehicle_bbox, stop_line, image):
    """Check if vehicle center is below (past) the stop line."""
    _, y1, _, y2 = vehicle_bbox
    veh_center_y = (y1 + y2) / 2
    return veh_center_y > stop_line['cy']


def check_stop_line_violation(detections, image):
    violations = []
    h, w = image.shape[:2]

    stop_lines = detect_stop_lines(image)
    if not stop_lines:
        return violations

    vehicles = [d for d in detections if d.get('class_id') in config.VEHICLE_CLASSES]
    if not vehicles:
        return violations

    # Use the longest stop line as reference
    stop_line = max(stop_lines, key=lambda s: s['length'])

    for veh in vehicles:
        if is_vehicle_past_stop_line(veh['bbox'], stop_line, image):
            vtype = config.VEHICLE_CLASSES.get(veh['class_id'], 'vehicle')
            violations.append({
                'violation_type': 'STOP_LINE_VIOLATION',
                'confidence': 0.50,
                'confidence_band': 'low',
                'vehicle_bbox': veh['bbox'],
                'vehicle_type': vtype,
                'severity_score': config.RISK_SCORES.get('STOP_LINE_VIOLATION', 60),
                'stop_line_y': int(stop_line['cy']),
                'description': f'{veh.get("instance_id", vtype)} crossed stop line',
                'involved_objects': [veh.get('instance_id', vtype)],
            })

    return violations
