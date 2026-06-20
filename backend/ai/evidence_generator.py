import cv2
import numpy as np
import os
from datetime import datetime
import config


COLORS = {
    'person': (0, 255, 0),
    'motorcycle': (255, 0, 0),
    'car': (0, 0, 255),
    'bus': (255, 255, 0),
    'truck': (255, 0, 255),
    'violation': (0, 0, 255),
    'plate': (0, 255, 255),
    'overloading': (255, 100, 150),
    'wrong_side': (255, 0, 255),
    'overloading': (0, 0, 255),
    'default': (255, 255, 255),
}


def get_color(label):
    return COLORS.get(label, COLORS['default'])


def generate_evidence(original_image, detections, violations, plate_info, source_filename="image"):
    image = original_image.copy()
    height, width = image.shape[:2]

    for det in detections:
        x1, y1, x2, y2 = [int(v) for v in det['bbox']]
        label = det.get('label', 'unknown')
        instance_id = det.get('instance_id', label)
        color = get_color(label)
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        text = f"{instance_id} {det['confidence']:.2f}"
        cv2.putText(image, text, (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    for violation in violations:
        vtype = violation['violation_type']
        if vtype == 'NO_HELMET':
            if 'person_bbox' in violation:
                x1, y1, x2, y2 = [int(v) for v in violation['person_bbox']]
                cv2.rectangle(image, (x1, y1), (x2, y2), COLORS['violation'], 3)
                cv2.putText(image, 'NO HELMET', (x1, y1 - 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS['violation'], 2)
        elif vtype == 'TRIPLE_RIDING':
            if 'motorcycle_bbox' in violation:
                x1, y1, x2, y2 = [int(v) for v in violation['motorcycle_bbox']]
                cv2.rectangle(image, (x1, y1), (x2, y2), COLORS['violation'], 3)
                cv2.putText(image, f"TRIPLE RIDING ({violation.get('rider_count', 0)})",
                            (x1, y1 - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            COLORS['violation'], 2)
            for rider in violation.get('riders', []):
                x1, y1, x2, y2 = [int(v) for v in rider['bbox']]
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 165, 255), 2)
                cv2.putText(image, 'RIDER', (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
        elif vtype == 'MOTORCYCLE_OVERLOADING':
            if 'motorcycle_bbox' in violation:
                x1, y1, x2, y2 = [int(v) for v in violation['motorcycle_bbox']]
                cv2.rectangle(image, (x1, y1), (x2, y2), COLORS['overloading'], 4)
                cv2.putText(image, f"OVERLOADING ({violation.get('rider_count', 0)} riders)",
                            (x1, y1 - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            COLORS['overloading'], 2)
            for rider in violation.get('riders', []):
                x1, y1, x2, y2 = [int(v) for v in rider['bbox']]
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(image, 'RIDER', (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        elif vtype == 'WRONG_SIDE_DRIVING':
            if 'vehicle_bbox' in violation:
                x1, y1, x2, y2 = [int(v) for v in violation['vehicle_bbox']]
                cv2.rectangle(image, (x1, y1), (x2, y2), COLORS['wrong_side'], 3)
                cv2.putText(image, 'WRONG SIDE', (x1, y1 - 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS['wrong_side'], 2)

    if plate_info and plate_info[0]:
        plate_text, plate_conf = plate_info
        cv2.putText(image, f"Plate: {plate_text} ({plate_conf:.2f})",
                    (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, COLORS['plate'], 2)

    header_y = 30
    cv2.putText(image, f"TRINETRA AI - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                (10, header_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    if violations:
        y_offset = header_y + 25
        for v in violations:
            text = f"Violation: {v['violation_type']}"
            cv2.putText(image, text, (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            y_offset += 20

    source_basename = os.path.splitext(os.path.basename(source_filename))[0]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    evidence_path = os.path.join(config.EVIDENCE_DIR, f'{source_basename}_evidence_{timestamp}.jpg')
    cv2.imwrite(evidence_path, image)
    return evidence_path
