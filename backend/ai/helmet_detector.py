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


def is_person_on_motorcycle(person_bbox, motorcycle_bbox):
    return iou(person_bbox, motorcycle_bbox) > 0.15


def detect_helmet_in_head_region(image, person_bbox):
    x1, y1, x2, y2 = [int(v) for v in person_bbox]
    head_y2 = y1 + int((y2 - y1) * 0.25)
    head_region = image[y1:head_y2, x1:x2]
    if head_region.size == 0:
        return False
    hsv = cv2.cvtColor(head_region, cv2.COLOR_BGR2HSV)
    height, width = head_region.shape[:2]
    total_pixels = height * width
    if total_pixels == 0:
        return False

    kernel = np.ones((5, 5), np.uint8)
    for color_name, (lower, upper) in config.HELMET_COLORS_HSV.items():
        lower = np.array(lower, dtype=np.uint8)
        upper = np.array(upper, dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        helmet_pixels = cv2.countNonZero(mask)
        ratio = helmet_pixels / total_pixels
        if ratio > 0.35:
            return True
    return False


def check_helmet_violation(detections, image):
    persons = [d for d in detections if d['class_id'] == config.PERSON_CLASS_ID]
    motorcycles = [d for d in detections if d['class_id'] == config.MOTORCYCLE_CLASS_ID]
    violations = []
    for person in persons:
        for motorcycle in motorcycles:
            if is_person_on_motorcycle(person['bbox'], motorcycle['bbox']):
                has_helmet = detect_helmet_in_head_region(image, person['bbox'])
                if not has_helmet:
                    violations.append({
                        'violation_type': 'NO_HELMET',
                        'confidence': person['confidence'],
                        'person_bbox': person['bbox'],
                        'motorcycle_bbox': motorcycle['bbox'],
                        'description': 'Rider without helmet detected',
                    })
                break
    return violations
