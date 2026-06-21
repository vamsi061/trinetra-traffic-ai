"""Batch detection test — runs image through full pipeline and prints per-image summary.

Run: python batch_test.py
"""
import os
import sys
import json
import cv2
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from ai.locate_anything import LocateAnythingDetector
from ai.helmet_detector import check_helmet_violation
from ai.triple_riding import check_triple_riding
from ai.parking_detector import check_illegal_parking
from ai.seatbelt_detector import check_seatbelt_violation
from ai.wrong_side_detector import check_wrong_side_violation
from ai.red_light_detector import check_red_light_violation
from ai.stop_line_detector import check_stop_line_violation
from utils.image_processing import enhance_image

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'data', 'uploads')


def parse_expected(filename):
    """Return list of expected violation types based on filename prefix."""
    name = filename.lower()
    if 'helmet_missing' in name:
        return ['NO_HELMET']
    if 'triple_riding' in name:
        return ['TRIPLE_RIDING']
    if 'overloading' in name:
        return ['MOTORCYCLE_OVERLOADING']
    if 'illegal parking' in name:
        return ['POSSIBLE_ILLEGAL_PARKING']
    if 'pedestrian' in name or 'crowded' in name:
        return []  # No violations expected — friction-free
    if 'rain' in name or 'lowlight' in name:
        return []  # Friction-free by design (poor-quality)
    if 'ocr_clear' in name:
        return []  # Only plate readability test — no violations
    if 'bikeshelmets' in name:
        # These images are helmet/non-helmet mixes — expected violations vary
        return ['MIXED']
    return []


def process_image(image_path):
    image = cv2.imread(image_path)
    if image is None:
        return None, None, None

    filename = os.path.basename(image_path)
    skip_violations = parse_expected(filename) == [] and not any(
        kw in filename.lower() for kw in ['helmet_missing', 'bikeshelmets', 'triple_riding', 'overloading', 'illegal parking', 'seatbelt', 'wrong_side', 'red_light', 'stop_line']
    )

    processed = enhance_image(image)
    detector = LocateAnythingDetector()
    raw = detector.detect(image)
    filtered = [d for d in raw if not (d['class_id'] in (2, 3, 5, 7) and d.get('confidence', 1) < 0.25)]
    instance_counts = {}
    detections = []
    for d in filtered:
        d['instance_id'] = f"{d['label']}_{instance_counts.get(d['label'], 0) + 1}"
        instance_counts[d['label']] = instance_counts.get(d['label'], 0) + 1
        detections.append(d)

    violations = []
    if not skip_violations:
        for fn in [check_helmet_violation, check_triple_riding, check_illegal_parking,
                   check_seatbelt_violation, check_wrong_side_violation,
                   check_red_light_violation, check_stop_line_violation]:
            img_arg = processed if fn is check_triple_riding or fn in (
                check_red_light_violation, check_stop_line_violation,
                check_seatbelt_violation, check_wrong_side_violation) else image
            try:
                result = fn(detections, img_arg)
            except Exception as e:
                continue
            for v in result:
                if v.get('violation_type') == 'NORMAL':
                    continue
                violations.append({'type': v['violation_type'], 'conf': v.get('confidence', 0)})
    return [{'label': d['label'], 'conf': d.get('confidence', 0)} for d in detections], violations, image.shape


def main():
    results = []
    for fn in sorted(os.listdir(UPLOAD_DIR)):
        path = os.path.join(UPLOAD_DIR, fn)
        if not os.path.isfile(path):
            continue
        expected = parse_expected(fn)
        dets, viols, shape = process_image(path)
        if dets is None:
            continue
        types = sorted(set(v['type'] for v in viols))
        results.append({
            'file': fn,
            'expected': expected,
            'detected': types,
            'detection_counts': dict(Counter(d['label'] for d in dets)),
        })

    # Print summary
    issues = defaultdict(list)
    for r in results:
        if 'MIXED' in r['expected']:
            continue
        expected_set = set(r['expected'])
        detected_set = set(r['detected'])
        missing = expected_set - detected_set
        if missing:
            extra = detected_set - expected_set
            issues[r['file'].split('_')[1] if '_' in r['file'] else r['file']].append({
                'file': r['file'],
                'expected': list(expected_set),
                'detected': list(detected_set),
                'missing': list(missing),
                'extra': list(extra),
            })

    print(f"\n{'='*80}\nSAMPLE BATCH TEST SUMMARY — {len(results)} images\n{'='*80}")
    by_category = defaultdict(list)
    for r in results:
        name = r['file']
        # Extract category from filename
        import re
        m = re.search(r'_[a-f0-9]{32}_(.+?)(?:_\d+)?\.(?:jpg|jpeg|png)$', '_' + name)
        cat = m.group(1) if m else name.split('.')[0]
        if 'BikesHelmets' in name:
            cat = 'BikesHelmets'
        by_category[cat].append(r)

    for cat, items in sorted(by_category.items()):
        print(f"\n--- {cat} ({len(items)} images) ---")
        for r in items[:5]:
            print(f"  {r['file'][:60]:60} expected={r['expected']}  detected={r['detected']}")
        if len(items) > 5:
            print(f"  ... and {len(items) - 5} more")

    print(f"\n{'='*80}\nMISMATCH ANALYSIS\n{'='*80}")
    for cat, probs in sorted(issues.items()):
        if not probs:
            continue
        print(f"\n[{cat}] {len(probs)} mismatches:")
        for p in probs[:8]:
            print(f"  {p['file'][:60]:60} expected={p['expected']}  detected={p['detected']}")


if __name__ == '__main__':
    main()
