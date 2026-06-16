"""Performance evaluation for TRINETRA AI detection pipeline.

Computes:
  - Accuracy, Precision, Recall, F1-score
  - Mean Average Precision (mAP)
  - Per-class metrics
  - Inference speed benchmarks

Usage:
    python evaluate.py                          # Run evaluation with all test images
    python evaluate.py --samples path/to/dir    # Use custom sample directory
    python evaluate.py --benchmark              # Run speed benchmarks only
"""

import os
import sys
import time
import json
import argparse
import numpy as np
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import cv2
from ai.detector import ObjectDetector
from ai.helmet_detector import check_helmet_violation
from ai.triple_riding import check_triple_riding
from ai.seatbelt_detector import check_seatbelt_violation
from ai.wrong_side_detector import check_wrong_side_violation
from ai.ocr import LicensePlateReader
from utils.image_processing import enhance_image
import config

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), 'tests', 'samples')


def load_ground_truth(samples_dir):
    ground_truth = {}
    label_map = {
        'test1_no_helmet.jpg': {'violations': ['NO_HELMET'], 'objects': ['motorcycle', 'person']},
        'test2_with_helmet.jpg': {'violations': [], 'objects': ['motorcycle', 'person']},
        'test3_triple_riding.jpg': {'violations': ['TRIPLE_RIDING'], 'objects': ['motorcycle', 'person', 'person', 'person']},
        'test4_car_plate.jpg': {'violations': [], 'objects': ['car']},
        'test5_compliant.jpg': {'violations': [], 'objects': ['motorcycle', 'person', 'person']},
        'test6_no_vehicle.jpg': {'violations': [], 'objects': []},
    }
    for fname in os.listdir(samples_dir):
        if fname in label_map:
            ground_truth[fname] = label_map[fname]
    return ground_truth


def compute_metrics(y_true, y_pred):
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)

    total = tp + fp + fn + tn
    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        'accuracy': round(accuracy, 4),
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'f1_score': round(f1, 4),
        'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
    }


def compute_map(detections_list, ground_truths_list, iou_threshold=0.5):
    all_ious = []
    for dets, gts in zip(detections_list, ground_truths_list):
        for d in dets:
            for g in gts:
                x1 = max(d['bbox'][0], g['bbox'][0])
                y1 = max(d['bbox'][1], g['bbox'][1])
                x2 = min(d['bbox'][2], g['bbox'][2])
                y2 = min(d['bbox'][3], g['bbox'][3])
                inter = max(0, x2 - x1) * max(0, y2 - y1)
                area_d = (d['bbox'][2] - d['bbox'][0]) * (d['bbox'][3] - d['bbox'][1])
                area_g = (g['bbox'][2] - g['bbox'][0]) * (g['bbox'][3] - g['bbox'][1])
                union = area_d + area_g - inter
                iou_val = inter / union if union > 0 else 0
                all_ious.append(iou_val > iou_threshold)

    if not all_ious:
        return 0.0
    return round(sum(all_ious) / len(all_ious), 4)


def run_evaluation(samples_dir):
    print("\n" + "=" * 65)
    print("  TRINETRA AI — Performance Evaluation")
    print("=" * 65)

    ground_truth = load_ground_truth(samples_dir)
    if not ground_truth:
        print("  ⚠ No ground truth data found. Using auto-generated labels.")
        for fname in sorted(os.listdir(samples_dir)):
            if fname.endswith(('.jpg', '.png')):
                violations = []
                if 'no_helmet' in fname:
                    violations.append('NO_HELMET')
                if 'triple' in fname:
                    violations.append('TRIPLE_RIDING')
                ground_truth[fname] = {'violations': violations, 'objects': []}

    detector = ObjectDetector()
    all_vtypes = set()
    y_true_all = []
    y_pred_all = []

    violation_results = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0, 'tn': 0})
    per_image_results = []
    inference_times = []

    for fname, gt in sorted(ground_truth.items()):
        path = os.path.join(samples_dir, fname)
        if not os.path.exists(path):
            continue

        img = cv2.imread(path)
        if img is None:
            continue

        t0 = time.time()
        processed = enhance_image(img)
        detections = detector.detect(processed)

        violations = []
        for v in check_helmet_violation(detections, processed):
            violations.append(v)
        for v in check_triple_riding(detections):
            violations.append(v)
        for v in check_seatbelt_violation(detections, processed):
            violations.append(v)
        for v in check_wrong_side_violation(detections, processed):
            violations.append(v)

        inference_time = (time.time() - t0) * 1000
        inference_times.append(inference_time)

        predicted_vtypes = set(v['violation_type'] for v in violations)
        gt_vtypes = set(gt.get('violations', []))

        all_vtypes.update(gt_vtypes | predicted_vtypes)

        for vtype in all_vtypes:
            if vtype in gt_vtypes and vtype in predicted_vtypes:
                violation_results[vtype]['tp'] += 1
            elif vtype not in gt_vtypes and vtype in predicted_vtypes:
                violation_results[vtype]['fp'] += 1
            elif vtype in gt_vtypes and vtype not in predicted_vtypes:
                violation_results[vtype]['fn'] += 1
            else:
                violation_results[vtype]['tn'] += 1

        per_image_results.append({
            'image': fname,
            'gt': list(gt_vtypes),
            'predicted': list(predicted_vtypes),
            'inference_ms': round(inference_time, 1),
            'detection_count': len(detections),
        })

        y_true_all.extend([1 if v in gt_vtypes else 0 for v in all_vtypes])
        y_pred_all.extend([1 if v in predicted_vtypes else 0 for v in all_vtypes])

    print(f"\n{'─' * 65}")
    print(f"  Dataset: {len(per_image_results)} images evaluated")
    print(f"{'─' * 65}")

    print(f"\n  {'Per-Image Results':^61}")
    print(f"  {'─' * 61}")
    header = f"  {'Image':<30} {'GT':<20} {'Predicted':<20} {'Time(ms)':<10}"
    print(header)
    print(f"  {'─' * 61}")
    for r in per_image_results:
        gt_str = ','.join(r['gt']) if r['gt'] else '—'
        pred_str = ','.join(r['predicted']) if r['predicted'] else '—'
        print(f"  {r['image']:<30} {gt_str:<20} {pred_str:<20} {r['inference_ms']:<10.1f}")

    print(f"\n  {'─' * 65}")
    print(f"  {'Overall Metrics':^61}")
    print(f"  {'─' * 65}")
    overall = compute_metrics(y_true_all, y_pred_all)
    for key in ['accuracy', 'precision', 'recall', 'f1_score']:
        print(f"  {key.replace('_', ' ').title():<20} {overall[key]:.4f}")
    print(f"  {'TP':<20} {overall['tp']}   {'FP':<20} {overall['fp']}")
    print(f"  {'FN':<20} {overall['fn']}   {'TN':<20} {overall['tn']}")

    print(f"\n  {'─' * 65}")
    print(f"  {'Per-Violation Metrics':^61}")
    print(f"  {'─' * 65}")
    for vtype in sorted(all_vtypes):
        r = violation_results[vtype]
        prec = r['tp'] / (r['tp'] + r['fp']) if (r['tp'] + r['fp']) > 0 else 0.0
        rec = r['tp'] / (r['tp'] + r['fn']) if (r['tp'] + r['fn']) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        print(f"  {vtype:<25} Precision: {prec:.3f}  Recall: {rec:.3f}  F1: {f1:.3f}")

    if inference_times:
        print(f"\n  {'─' * 65}")
        print(f"  {'Performance Benchmarks':^61}")
        print(f"  {'─' * 65}")
        print(f"  {'Avg Inference':<25} {np.mean(inference_times):.1f} ms")
        print(f"  {'Min Inference':<25} {np.min(inference_times):.1f} ms")
        print(f"  {'Max Inference':<25} {np.max(inference_times):.1f} ms")
        print(f"  {'Std Dev':<25} {np.std(inference_times):.1f} ms")
        print(f"  {'Throughput':<25} {1000 / np.mean(inference_times):.1f} images/sec")

    print(f"\n{'=' * 65}\n")
    return overall


def run_benchmark(samples_dir):
    print("\n" + "=" * 65)
    print("  TRINETRA AI — Speed Benchmark")
    print("=" * 65)

    detector = ObjectDetector()
    reader = LicensePlateReader()
    reader.load_reader()

    image_files = [f for f in sorted(os.listdir(samples_dir))
                   if f.endswith(('.jpg', '.png'))]
    if not image_files:
        print("  ⚠ No images found in samples directory.")
        return

    print(f"\n  Benchmarking with {len(image_files)} images...\n")

    stages = {
        'full_pipeline': [],
        'yolo_detection': [],
        'helmet_check': [],
        'triple_check': [],
        'seatbelt_check': [],
        'wrong_side_check': [],
        'plate_ocr': [],
    }

    for fname in image_files:
        path = os.path.join(samples_dir, fname)
        img = cv2.imread(path)
        if img is None:
            continue

        processed = enhance_image(img)

        t0 = time.time()
        detections = detector.detect(processed)
        stages['yolo_detection'].append((time.time() - t0) * 1000)

        t0 = time.time()
        check_helmet_violation(detections, processed)
        stages['helmet_check'].append((time.time() - t0) * 1000)

        t0 = time.time()
        check_triple_riding(detections)
        stages['triple_check'].append((time.time() - t0) * 1000)

        t0 = time.time()
        check_seatbelt_violation(detections, processed)
        stages['seatbelt_check'].append((time.time() - t0) * 1000)

        t0 = time.time()
        check_wrong_side_violation(detections, processed)
        stages['wrong_side_check'].append((time.time() - t0) * 1000)

        vehicles = detector.detect_vehicles(processed)
        t0 = time.time()
        if vehicles:
            biggest = max(vehicles, key=lambda v:
                (v['bbox'][2] - v['bbox'][0]) * (v['bbox'][3] - v['bbox'][1]))
            reader.read_plate(processed, biggest['bbox'])
        stages['plate_ocr'].append((time.time() - t0) * 1000)

    print(f"  {'Stage':<25} {'Avg(ms)':<12} {'Min(ms)':<12} {'Max(ms)':<12}")
    print(f"  {'─' * 61}")
    for stage, times in stages.items():
        if times:
            print(f"  {stage:<25} {np.mean(times):<12.1f} {np.min(times):<12.1f} {np.max(times):<12.1f}")

    print(f"\n{'=' * 65}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--samples', default=SAMPLES_DIR)
    parser.add_argument('--benchmark', action='store_true')
    parser.add_argument('--output', help='Save results as JSON')
    args = parser.parse_args()

    if args.benchmark:
        run_benchmark(args.samples)
    else:
        results = run_evaluation(args.samples)
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Results saved to {args.output}")
