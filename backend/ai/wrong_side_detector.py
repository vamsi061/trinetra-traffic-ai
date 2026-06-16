import cv2
import numpy as np
import config


def detect_lane_lines(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    h, w = image.shape[:2]
    roi_vertices = [
        (0, h),
        (w * 0.05, h * 0.5),
        (w * 0.95, h * 0.5),
        (w, h),
    ]
    mask = np.zeros_like(gray)
    cv2.fillPoly(mask, np.array([roi_vertices], dtype=np.int32), 255)
    masked_edges = cv2.bitwise_and(edges, mask)

    lines = cv2.HoughLinesP(
        masked_edges, rho=1, theta=np.pi / 180,
        threshold=40, minLineLength=40, maxLineGap=30
    )
    return lines


def classify_lane_lines(lines, image_width):
    left_lines = []
    right_lines = []
    cx = image_width / 2

    if lines is None:
        return left_lines, right_lines

    for line in lines:
        x1, y1, x2, y2 = line[0]
        slope = (y2 - y1) / (x2 - x1 + 1e-6)
        if 0.2 < abs(slope) < 3.0:
            line_cx = (x1 + x2) / 2
            # Left lane line: positive slope on left side of image
            if slope > 0 and line_cx < cx:
                left_lines.append(line)
            # Right lane line: negative slope on right side of image
            elif slope < 0 and line_cx > cx:
                right_lines.append(line)

    return left_lines, right_lines


def get_average_lane_angle(lines):
    if not lines:
        return None
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        angles.append(angle)
    return np.mean(angles)


def is_vehicle_wrong_side(vehicle_bbox, left_lines, right_lines, image_width):
    vx = (vehicle_bbox[0] + vehicle_bbox[2]) / 2
    vw = vehicle_bbox[2] - vehicle_bbox[0]
    vh = vehicle_bbox[3] - vehicle_bbox[1]

    num_left = len(left_lines) if left_lines else 0
    num_right = len(right_lines) if right_lines else 0

    total_lines = num_left + num_right
    if total_lines < 4:
        return False, 0.0

    ratio = max(num_left, num_right) / total_lines
    if ratio < 0.7:
        return False, 0.0

    vehicle_center_is_left = vx < image_width * 0.4
    vehicle_center_is_right = vx > image_width * 0.6

    more_left = num_left > num_right

    if more_left and vehicle_center_is_left:
        return True, round(num_left / total_lines, 2)
    if not more_left and vehicle_center_is_right:
        return True, round(num_right / total_lines, 2)

    return False, 0.0


def check_wrong_side_violation(detections, image):
    violations = []
    vehicles = [d for d in detections if d['class_id'] in config.VEHICLE_CLASSES]

    if not vehicles:
        return violations

    lines = detect_lane_lines(image)
    if lines is None:
        return violations

    left_lines, right_lines = classify_lane_lines(lines, image.shape[1])
    if len(left_lines) + len(right_lines) < 4:
        return violations

    for vehicle in vehicles:
        wrong_side, confidence = is_vehicle_wrong_side(
            vehicle['bbox'], left_lines, right_lines, image.shape[1]
        )
        if wrong_side:
            vtype = config.VEHICLE_CLASSES.get(vehicle['class_id'], 'vehicle')
            violations.append({
                'violation_type': 'WRONG_SIDE_DRIVING',
                'confidence': confidence,
                'vehicle_bbox': vehicle['bbox'],
                'vehicle_type': vtype,
                'description': f'{vtype.capitalize()} driving on wrong side of road',
            })

    return violations
