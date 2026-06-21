import cv2
import numpy as np
import config


def detect_stop_lines(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    h, w = image.shape[:2]

    # Focus on lower-middle portion where stop lines are visible
    roi_y1 = int(h * 0.50)
    roi = edges[roi_y1:int(h * 0.85), :]

    if roi.shape[0] < 20:
        return []

    lines = cv2.HoughLinesP(
        roi, rho=1, theta=np.pi / 180,
        threshold=50, minLineLength=int(w * 0.45), maxLineGap=20
    )

    if lines is None:
        return []

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

        stop_lines.append({
            'x1': x1, 'y1': y1 + roi_y1,
            'x2': x2, 'y2': y2 + roi_y1,
            'cx': line_cx, 'cy': line_cy,
            'length': line_len,
        })

    return stop_lines


def is_vehicle_past_stop_line(vehicle_bbox, stop_line, image):
    """Check if vehicle is clearly past the stop line."""
    _, y1, _, y2 = vehicle_bbox
    veh_center_y = (y1 + y2) / 2
    veh_bottom = y2
    return veh_bottom > stop_line['cy'] and (veh_center_y - stop_line['cy']) > image.shape[0] * 0.03


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
        # Only consider vehicles that are large enough (close to camera)
        veh_h = veh['bbox'][3] - veh['bbox'][1]
        veh_w = veh['bbox'][2] - veh['bbox'][0]
        veh_area = veh_h * veh_w
        img_area = h * w
        
        # Vehicle must be at least 2% of image area to be considered
        if veh_area / img_area < 0.02:
            continue
            
        # Vehicle must be in the bottom half of the image
        if veh['bbox'][3] < h * 0.45:
            continue
            
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
