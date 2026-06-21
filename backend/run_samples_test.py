"""Test harness: run the detection pipeline on each sample image and report
detected violations vs. the expected violation encoded in the filename.

Usage (from backend/ dir):
    python run_samples_test.py
"""
import os, sys, glob
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from utils.image_processing import enhance_image
from ai.locate_anything import LocateAnythingDetector
from ai.helmet_detector import check_helmet_violation
from ai.triple_riding import check_triple_riding
from ai.parking_detector import check_illegal_parking
from ai.seatbelt_detector import check_seatbelt_violation
from ai.wrong_side_detector import check_wrong_side_violation
from ai.red_light_detector import check_red_light_violation
from ai.stop_line_detector import check_stop_line_violation
from ai.rider_association import associate_riders

UPLOAD_DIR = os.path.join(config.DATA_DIR, 'uploads')

EXPECT_MAP = {
    'HELMET_MISSING': ['NO_HELMET'],
    'TRIPLE_RIDING': ['TRIPLE_RIDING'],
    'OVERLOADING': ['MOTORCYCLE_OVERLOADING', 'MOTORCYCLE_EXTREME_OVERLOADING', 'TRIPLE_RIDING'],
    'ILLEGAL PARKING': ['POSSIBLE_ILLEGAL_PARKING'],
    'BikesHelmets': [],
    'CROWDED': [],
    'LOWLIGHT': [],
    'OCR_CLEAR': [],
    'PEDESTRIAN': [],
    'RAIN': [],
}


def unique_samples():
    seen = {}
    for p in sorted(glob.glob(os.path.join(UPLOAD_DIR, '*'))):
        name = os.path.basename(p)
        suffix = name.split('_', 1)[1] if '_' in name else name
        seen[suffix] = p
    return seen


def expected_for(suffix):
    for token, exp in EXPECT_MAP.items():
        if suffix.startswith(token):
            return exp
    return []


def run_one(detector, path):
    image = cv2.imread(path)
    if image is None:
        return None, 'failed to read'
    processed = enhance_image(image)
    raw_detections = detector.detect(image)

    filtered = []
    for d in raw_detections:
        if d['class_id'] in (2, 3, 5, 7) and d['confidence'] < config.VEHICLE_CONFIDENCE_THRESHOLD:
            continue
        filtered.append(d)

    instance_counts = {}
    detections = []
    for d in filtered:
        label = d['label']
        instance_counts[label] = instance_counts.get(label, 0) + 1
        d['instance_id'] = f"{label}_{instance_counts[label]}"
        detections.append(d)

    person_count = len([d for d in detections if d['label'] == 'person'])
    motorcycle_count = len([d for d in detections if d['label'] == 'motorcycle'])
    crowded_scene = person_count >= 6 or (person_count >= 4 and motorcycle_count >= 2)

    violations = []
    for fn in [check_helmet_violation, check_triple_riding, check_seatbelt_violation,
               check_wrong_side_violation, check_red_light_violation, check_stop_line_violation]:
        img_arg = image
        if fn is check_triple_riding:
            img_arg = processed
        elif fn in (check_red_light_violation, check_stop_line_violation,
                    check_seatbelt_violation, check_wrong_side_violation):
            img_arg = processed
        for v in fn(detections, img_arg):
            if v['violation_type'] == 'NORMAL':
                continue
            violations.append(v)

    has_mc = any(d['label'] == 'motorcycle' for d in detections)
    has_person = any(d['label'] == 'person' for d in detections)
    persons_mc = [d for d in detections if d['label'] == 'person']
    motorcycles = [d for d in detections if d['label'] == 'motorcycle']
    mc_associations = associate_riders(persons_mc, motorcycles, processed.shape[:2])
    has_mounted_rider = has_mc and has_person and any(a.get('rider_count', 0) > 0 for a in mc_associations)
    ALL_VT = ('NO_HELMET', 'TRIPLE_RIDING', 'MOTORCYCLE_OVERLOADING',
              'MOTORCYCLE_EXTREME_OVERLOADING', 'POSSIBLE_ILLEGAL_PARKING',
              'SEATBELT_VIOLATION', 'WRONG_SIDE_DRIVING', 'RED_LIGHT_VIOLATION', 'STOP_LINE_VIOLATION')
    has_actual = any(v['violation_type'] in ALL_VT for v in violations)
    is_moving_hint = has_mounted_rider or (not has_actual and has_mc)
    parking_violations = check_illegal_parking(detections, image, moving_vehicle_hint=is_moving_hint)
    violations.extend(parking_violations)

    detected_types = sorted(set(v['violation_type'] for v in violations))
    labels = sorted(set(d['label'] for d in detections))
    return {
        'detected_types': detected_types,
        'labels': labels,
        'n_detections': len(detections),
        'n_person': person_count,
        'n_motorcycle': motorcycle_count,
        'crowded': crowded_scene,
    }, None


def main():
    detector = LocateAnythingDetector()
    samples = unique_samples()
    print(f"Found {len(samples)} unique samples\n")
    print(f"{'SAMPLE':<26} {'EXPECTED':<32} {'DETECTED':<48} {'LABELS'}")
    print('-' * 150)
    for suffix, path in sorted(samples.items()):
        res, err = run_one(detector, path)
        exp = expected_for(suffix)
        exp_s = ','.join(exp) if exp else '(none/FP-test)'
        if err:
            print(f"{suffix:<26} {exp_s:<32} ERROR: {err}")
            continue
        det_s = ','.join(res['detected_types']) if res['detected_types'] else '(none)'
        labels = f"{res['labels']} p={res['n_person']} mc={res['n_motorcycle']}{' CROWD' if res['crowded'] else ''}"
        flag = ''
        if exp:
            missing = [e for e in exp if e not in res['detected_types']]
            if missing:
                flag = ' [MISSING: ' + ','.join(missing) + ']'
        else:
            if res['detected_types']:
                flag = ' [FALSE POSITIVE!]'
        print(f"{suffix:<26} {exp_s:<32} {det_s:<48} {labels}{flag}")


if __name__ == '__main__':
    main()
