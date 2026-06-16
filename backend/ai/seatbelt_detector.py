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
    return iou(person_bbox, car_bbox) > config.SEATBELT_IoU_THRESHOLD


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

    h, w = torso_region.shape[:2]
    cx, cy = w // 2, h // 2
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
        if dist < w * 0.4:
            diagonal_count += 1

    # Require at least 2 diagonal lines to confirm seatbelt
    return diagonal_count >= 2


def check_seatbelt_violation(detections, image):
    persons = [d for d in detections if d['class_id'] == config.PERSON_CLASS_ID]
    cars = [d for d in detections if d['class_id'] == config.CAR_CLASS_ID]
    violations = []

    for person in persons:
        for car in cars:
            if is_person_in_car(person['bbox'], car['bbox']):
                has_seatbelt = detect_seatbelt_in_torso(image, person['bbox'])
                if has_seatbelt is False:
                    violations.append({
                        'violation_type': 'SEATBELT_VIOLATION',
                        'confidence': person['confidence'],
                        'person_bbox': person['bbox'],
                        'vehicle_bbox': car['bbox'],
                        'description': f'{person.get("instance_id", "Person")} without seatbelt in {car.get("instance_id", "car")}',
                        'involved_objects': [
                            person.get('instance_id', 'person'),
                            car.get('instance_id', 'car'),
                        ],
                    })
                break
    return violations
