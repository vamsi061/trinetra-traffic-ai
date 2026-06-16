import cv2
import numpy as np
from ai.rider_association import associate_riders
import config


def detect_helmet_in_head_region(image, person_bbox):
    """Enhanced HSV-based helmet detection with multi-scale analysis."""
    x1, y1, x2, y2 = [int(v) for v in person_bbox]
    person_h = y2 - y1
    person_w = x2 - x1

    if person_h < 20 or person_w < 10:
        return False, 0.0

    # Head region: upper 30% of person bbox (expanded from 25% to capture full head)
    head_y2 = y1 + int(person_h * 0.30)
    head_region = image[y1:head_y2, x1:x2]

    if head_region.size == 0:
        return False, 0.0

    h, w = head_region.shape[:2]
    total_pixels = h * w
    if total_pixels == 0:
        return False, 0.0

    hsv = cv2.cvtColor(head_region, cv2.COLOR_BGR2HSV)

    # Adaptive histogram equalization — only if image has enough variance
    hsv_eq = hsv
    try:
        gray_head = cv2.cvtColor(head_region, cv2.COLOR_BGR2GRAY)
        if gray_head.std() > 15:  # skip CLAHE for near-uniform regions
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray_head)
            hsv_eq = cv2.cvtColor(cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR), cv2.COLOR_BGR2HSV)
    except Exception:
        pass

    kernel = np.ones((5, 5), np.uint8)
    max_ratio = 0.0

    for color_name, (lower, upper) in config.HELMET_COLORS_HSV.items():
        lower = np.array(lower, dtype=np.uint8)
        upper = np.array(upper, dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        helmet_pixels = cv2.countNonZero(mask)
        ratio = helmet_pixels / total_pixels

        if hsv_eq is not hsv:
            mask_eq = cv2.inRange(hsv_eq, lower, upper)
            mask_eq = cv2.morphologyEx(mask_eq, cv2.MORPH_CLOSE, kernel)
            mask_eq = cv2.morphologyEx(mask_eq, cv2.MORPH_OPEN, kernel)
            ratio_eq = cv2.countNonZero(mask_eq) / total_pixels
            ratio = max(ratio, ratio_eq)

        if ratio > max_ratio:
            max_ratio = ratio

    # Threshold 0.25 for helmet detection
    has_helmet = max_ratio > 0.25
    confidence = min(max_ratio * 1.5, 1.0)
    return has_helmet, confidence


def check_helmet_violation(detections, image):
    persons = [d for d in detections if d['class_id'] == config.PERSON_CLASS_ID]
    motorcycles = [d for d in detections if d['class_id'] == config.MOTORCYCLE_CLASS_ID]

    img_shape = image.shape[:2] if image is not None else (None, None)
    associations = associate_riders(persons, motorcycles, img_shape)

    violations = []
    for assoc in associations:
        mc = assoc['motorcycle']
        for person in assoc['riders']:
            has_helmet, helmet_conf = detect_helmet_in_head_region(image, person['bbox'])
            if not has_helmet:
                violations.append({
                    'violation_type': 'NO_HELMET',
                    'confidence': helmet_conf,
                    'person_bbox': person['bbox'],
                    'motorcycle_bbox': mc['bbox'],
                    'severity_score': config.RISK_SCORES.get('NO_HELMET', 30),
                    'description': f'{person.get("instance_id", "Rider")} without helmet on {mc.get("instance_id", "motorcycle")}',
                    'involved_objects': [
                        person.get('instance_id', 'person'),
                        mc.get('instance_id', 'motorcycle'),
                    ],
                })
    return violations
