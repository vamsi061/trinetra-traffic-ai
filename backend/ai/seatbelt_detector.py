import cv2
import numpy as np
import config


def iou(box1, box2):
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0


def is_person_in_car(person_bbox, car_bbox):
    """Strict check: person must be substantially inside the car bbox.
    At least 40% of person area must overlap with car bbox (containment)."""
    x1 = max(person_bbox[0], car_bbox[0])
    y1 = max(person_bbox[1], car_bbox[1])
    x2 = min(person_bbox[2], car_bbox[2])
    y2 = min(person_bbox[3], car_bbox[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    person_area = (person_bbox[2] - person_bbox[0]) * (person_bbox[3] - person_bbox[1])
    if person_area <= 0:
        return False
    return inter / person_area >= 0.40


def detect_seatbelt_in_torso(image, person_bbox):
    x1, y1, x2, y2 = [int(v) for v in person_bbox]
    person_h = y2 - y1
    person_w = x2 - x1

    if person_h < 40 or person_w < 20:
        return None

    torso_y1 = y1 + int(person_h * 0.25)
    torso_y2 = y1 + int(person_h * 0.55)
    torso_region = image[torso_y1:torso_y2, x1:x2]

    if torso_region.size == 0 or torso_region.shape[0] < 10 or torso_region.shape[1] < 10:
        return None

    gray = cv2.cvtColor(torso_region, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blurred, 40, 120)
    lines = cv2.HoughLinesP(
        edges, rho=1, theta=np.pi / 180,
        threshold=40, minLineLength=int(person_h * 0.15), maxLineGap=15
    )

    if lines is None:
        return False

    h_, w_ = torso_region.shape[:2]
    cx, cy = w_ // 2, h_ // 2
    diagonal_count = 0
    for line in lines:
        x1_l, y1_l, x2_l, y2_l = line[0]
        angle = abs(np.degrees(np.arctan2(y2_l - y1_l, x2_l - x1_l)))
        is_diagonal = 25 < angle < 65 or 115 < angle < 155
        if not is_diagonal:
            continue
        line_len = np.sqrt((x2_l - x1_l) ** 2 + (y2_l - y1_l) ** 2)
        if line_len < 15:
            continue
        line_cx = (x1_l + x2_l) / 2
        line_cy = (y1_l + y2_l) / 2
        dist = np.sqrt((line_cx - cx) ** 2 + (line_cy - cy) ** 2)
        if dist < w_ * 0.4:
            diagonal_count += 1

    return diagonal_count >= 2


def _is_likely_car(car_bbox, image_shape):
    """Filter out non-car vehicles misclassified as car (e.g. auto-rickshaws).
    Cars are wide (width > height * 0.7) and occupy meaningful image area.
    """
    h, w = image_shape[:2]
    x1, y1, x2, y2 = car_bbox
    car_w = x2 - x1
    car_h = y2 - y1
    car_area = car_w * car_h
    image_area = h * w

    # Must occupy at least 1.5% of image area
    if car_area / image_area < 0.015:
        return False

    # Must be at least 60px wide
    if car_w < 60:
        return False

    # Cars are wider than they are tall or slightly taller
    # Autos/three-wheelers are narrow (width/height < 0.6)
    aspect = car_w / car_h if car_h > 0 else 0
    if aspect < 0.55:
        return False

    return True


def check_seatbelt_violation(detections, image):
    """Seatbelt detection ONLY for car occupants — one violation per car."""
    persons = [d for d in detections if d['class_id'] == config.PERSON_CLASS_ID]
    cars = [d for d in detections if d['class_id'] == config.CAR_CLASS_ID and
            _is_likely_car(d['bbox'], image.shape)]

    if not cars:
        return []

    violations = []

    for car in cars:
        car_area = (car['bbox'][2] - car['bbox'][0]) * (car['bbox'][3] - car['bbox'][1])
        best_person = None
        best_overlap = 0.0

        for person in persons:
            if person['confidence'] < 0.5:
                continue
            if is_person_in_car(person['bbox'], car['bbox']):
                inter_area = max(0, min(person['bbox'][2], car['bbox'][2]) - max(person['bbox'][0], car['bbox'][0])) * \
                             max(0, min(person['bbox'][3], car['bbox'][3]) - max(person['bbox'][1], car['bbox'][1]))
                if inter_area > best_overlap:
                    best_overlap = inter_area
                    best_person = person

        if best_person and best_overlap > 0:
            has_seatbelt = detect_seatbelt_in_torso(image, best_person['bbox'])
            if has_seatbelt is False:
                violations.append({
                    'violation_type': 'SEATBELT_VIOLATION',
                    'confidence': best_person['confidence'],
                    'confidence_band': 'medium' if best_person['confidence'] >= 0.6 else 'low',
                    'person_bbox': best_person['bbox'],
                    'vehicle_bbox': car['bbox'],
                    'severity_score': config.RISK_SCORES.get('SEATBELT_VIOLATION', 40),
                    'description': f'{best_person.get("instance_id", "Person")} without seatbelt in {car.get("instance_id", "car")}',
                    'involved_objects': [
                        best_person.get('instance_id', 'person'),
                        car.get('instance_id', 'car'),
                    ],
                })
    return violations
