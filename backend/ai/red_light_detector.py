import cv2
import numpy as np
import config


def detect_traffic_light_color(tl_bbox, image):
    x1, y1, x2, y2 = [int(v) for v in tl_bbox]
    x1 = max(0, x1); y1 = max(0, y1)
    x2 = min(image.shape[1], x2); y2 = min(image.shape[0], y2)
    if x2 - x1 < 5 or y2 - y1 < 5:
        return None, 0.0, 0.0

    region = image[y1:y2, x1:x2]
    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    h, w = region.shape[:2]

    bulb_region = hsv[:int(h * 0.8), :]

    red_mask1 = cv2.inRange(bulb_region, np.array([0, 50, 50]), np.array([10, 255, 255]))
    red_mask2 = cv2.inRange(bulb_region, np.array([170, 50, 50]), np.array([180, 255, 255]))
    red_mask = red_mask1 | red_mask2

    yellow_mask = cv2.inRange(bulb_region, np.array([15, 50, 50]), np.array([35, 255, 255]))
    green_mask = cv2.inRange(bulb_region, np.array([40, 50, 50]), np.array([90, 255, 255]))

    red_px = cv2.countNonZero(red_mask)
    yellow_px = cv2.countNonZero(yellow_mask)
    green_px = cv2.countNonZero(green_mask)

    total = red_px + yellow_px + green_px
    if total < 10:
        return None, 0.0, 0.0

    bulb_area = bulb_region.shape[0] * bulb_region.shape[1]
    signal_visibility = min(1.0, red_px / max(bulb_area, 1))

    red_vals = bulb_region[..., 2][red_mask > 0]
    signal_brightness = float(np.mean(red_vals)) / 255.0 if len(red_vals) > 0 else 0.0

    if red_px > yellow_px and red_px > green_px:
        return 'red', signal_visibility, signal_brightness
    elif yellow_px > red_px and yellow_px > green_px:
        return 'yellow', signal_visibility, signal_brightness
    elif green_px > red_px and green_px > yellow_px:
        return 'green', signal_visibility, signal_brightness
    return None, signal_visibility, signal_brightness


def compute_stop_line_proximity(vehicle_bbox, image_height):
    """Score how likely the vehicle is past any stop line. 0.0 = not past, 1.0 = clearly past."""
    _, y1, _, y2 = vehicle_bbox
    veh_center_y = (y1 + y2) / 2
    veh_bottom = y2

    center_ratio = veh_center_y / image_height
    bottom_ratio = veh_bottom / image_height

    score = 0.0
    if bottom_ratio > 0.70:
        score += 0.5
    elif bottom_ratio > 0.55:
        score += 0.3

    if center_ratio > 0.55:
        score += 0.3
    elif center_ratio > 0.45:
        score += 0.15

    score += min(0.2, max(0, (bottom_ratio - 0.40) / 2.0))

    return min(1.0, score)


def assess_image_quality_for_red_light(image):
    """Return 0.0–1.0 quality score for red light detection."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray)) / 255.0

    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    sharpness = min(1.0, laplacian_var / 500.0)

    quality = 0.5 * brightness + 0.5 * sharpness
    return max(0.3, min(1.0, quality))


def check_red_light_violation(detections, image):
    violations = []
    h, w = image.shape[:2]

    traffic_lights = [d for d in detections if d.get('class_id') == 9]
    if not traffic_lights:
        return violations

    vehicles = [d for d in detections if d.get('class_id') in config.VEHICLE_CLASSES]
    if not vehicles:
        return violations

    red_tl_bbox = None
    signal_visibility = 0.0
    signal_brightness = 0.0
    for tl in traffic_lights:
        color, sv, sb = detect_traffic_light_color(tl['bbox'], image)
        if color == 'red':
            red_tl_bbox = tl['bbox']
            signal_visibility = sv
            signal_brightness = sb
            break

    if red_tl_bbox is None:
        return violations

    scene_quality = assess_image_quality_for_red_light(image)

    for veh in vehicles:
        vehicle_position = compute_stop_line_proximity(veh['bbox'], h)

        if vehicle_position < 0.30:
            continue

        confidence = (
            0.25 * signal_visibility +
            0.25 * signal_brightness +
            0.25 * vehicle_position +
            0.25 * scene_quality
        )
        confidence = max(0.30, min(0.98, confidence))

        conf_band = 'high' if confidence >= 0.80 else ('medium' if confidence >= 0.60 else 'low')

        vtype = config.VEHICLE_CLASSES.get(veh['class_id'], 'vehicle')
        violations.append({
            'violation_type': 'RED_LIGHT_VIOLATION',
            'confidence': round(confidence, 3),
            'confidence_band': conf_band,
            'vehicle_bbox': veh['bbox'],
            'vehicle_type': vtype,
            'traffic_light_bbox': red_tl_bbox,
            'severity_score': config.RISK_SCORES.get('RED_LIGHT_VIOLATION', 90),
            'description': f'{veh.get("instance_id", vtype)} crossed intersection during red light',
            'involved_objects': [veh.get('instance_id', vtype)],
            'red_light_diagnostics': {
                'signal_visibility': round(signal_visibility, 3),
                'signal_brightness': round(signal_brightness, 3),
                'vehicle_position_score': round(vehicle_position, 3),
                'scene_quality': round(scene_quality, 3),
            },
        })

    return violations
