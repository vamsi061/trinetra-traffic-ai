import cv2
import numpy as np
import config


def detect_traffic_light_color(tl_bbox, image):
    x1, y1, x2, y2 = [int(v) for v in tl_bbox]
    x1 = max(0, x1); y1 = max(0, y1)
    x2 = min(image.shape[1], x2); y2 = min(image.shape[0], y2)
    if x2 - x1 < 5 or y2 - y1 < 5:
        return None

    region = image[y1:y2, x1:x2]
    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)

    h, w = region.shape[:2]

    # The lit bulb is typically in the top/middle portion of a traffic light
    bulb_region = hsv[:int(h * 0.8), :]

    # Red ranges (HSV)
    red_mask1 = cv2.inRange(bulb_region, np.array([0, 50, 50]), np.array([10, 255, 255]))
    red_mask2 = cv2.inRange(bulb_region, np.array([170, 50, 50]), np.array([180, 255, 255]))
    red_mask = red_mask1 | red_mask2

    # Yellow range
    yellow_mask = cv2.inRange(bulb_region, np.array([15, 50, 50]), np.array([35, 255, 255]))

    # Green range
    green_mask = cv2.inRange(bulb_region, np.array([40, 50, 50]), np.array([90, 255, 255]))

    red_px = cv2.countNonZero(red_mask)
    yellow_px = cv2.countNonZero(yellow_mask)
    green_px = cv2.countNonZero(green_mask)

    total = red_px + yellow_px + green_px
    if total < 10:
        return None

    if red_px > yellow_px and red_px > green_px:
        return 'red'
    elif yellow_px > red_px and yellow_px > green_px:
        return 'yellow'
    elif green_px > red_px and green_px > yellow_px:
        return 'green'
    return None


def is_vehicle_past_stop_line(vehicle_bbox, image_height):
    """Heuristic: if vehicle center is in lower 40% of image, it's likely past any stop line."""
    _, y1, _, y2 = vehicle_bbox
    veh_center_y = (y1 + y2) / 2
    return veh_center_y > image_height * 0.55


def check_red_light_violation(detections, image):
    violations = []
    h, w = image.shape[:2]

    traffic_lights = [d for d in detections if d.get('class_id') == 9]
    if not traffic_lights:
        return violations

    vehicles = [d for d in detections if d.get('class_id') in config.VEHICLE_CLASSES]
    if not vehicles:
        return violations

    active_red = False
    for tl in traffic_lights:
        color = detect_traffic_light_color(tl['bbox'], image)
        if color == 'red':
            active_red = True
            break

    if not active_red:
        return violations

    for veh in vehicles:
        if is_vehicle_past_stop_line(veh['bbox'], h):
            vtype = config.VEHICLE_CLASSES.get(veh['class_id'], 'vehicle')
            violations.append({
                'violation_type': 'RED_LIGHT_VIOLATION',
                'confidence': 0.55,
                'confidence_band': 'low',
                'vehicle_bbox': veh['bbox'],
                'vehicle_type': vtype,
                'severity_score': config.RISK_SCORES.get('RED_LIGHT_VIOLATION', 90),
                'description': f'{veh.get("instance_id", vtype)} crossed intersection during red light',
                'involved_objects': [veh.get('instance_id', vtype)],
            })

    return violations
