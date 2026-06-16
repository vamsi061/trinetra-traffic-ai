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
    return iou(person_bbox, motorcycle_bbox) > 0.1


def check_triple_riding(detections):
    persons = [d for d in detections if d['class_id'] == config.PERSON_CLASS_ID]
    motorcycles = [d for d in detections if d['class_id'] == config.MOTORCYCLE_CLASS_ID]
    violations = []
    for motorcycle in motorcycles:
        riders = []
        for person in persons:
            if is_person_on_motorcycle(person['bbox'], motorcycle['bbox']):
                riders.append(person)
        if len(riders) > 2:
            violations.append({
                'violation_type': 'TRIPLE_RIDING',
                'confidence': min(r['confidence'] for r in riders),
                'rider_count': len(riders),
                'riders': riders,
                'motorcycle_bbox': motorcycle['bbox'],
                'description': f'{len(riders)} riders on motorcycle (exceeds limit of 2)',
            })
    return violations
