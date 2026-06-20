import os, sys, time, json, argparse
import numpy as np
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import cv2
from ai.locate_anything import LocateAnythingDetector
from ai.helmet_detector import check_helmet_violation
from ai.triple_riding import check_triple_riding
from ai.seatbelt_detector import check_seatbelt_violation
from ai.wrong_side_detector import check_wrong_side_violation
from ai.red_light_detector import check_red_light_violation
from ai.stop_line_detector import check_stop_line_violation
from ai.ocr import LicensePlateReader
from utils.image_processing import enhance_image
import config

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), 'tests', 'samples')
GROUND_TRUTH_FILE = os.path.join(SAMPLES_DIR, 'ground_truth.json')

ALL_VIOLATION_TYPES = [
    'NO_HELMET', 'TRIPLE_RIDING', 'MOTORCYCLE_OVERLOADING',
    'MOTORCYCLE_EXTREME_OVERLOADING', 'SEATBELT_VIOLATION',
    'WRONG_SIDE_DRIVING', 'RED_LIGHT_VIOLATION', 'STOP_LINE_VIOLATION',
]


def load_ground_truth(samples_dir):
    gt_file = os.path.join(samples_dir, 'ground_truth.json')
    if not os.path.exists(gt_file):
        return {}

    with open(gt_file) as f:
        default_gt = json.load(f)

    ground_truth = {}
    for fname in sorted(default_gt.keys()):
        fpath = os.path.join(samples_dir, fname)
        if os.path.exists(fpath):
            ground_truth[fname] = default_gt[fname]

    return ground_truth


def compute_metrics(y_true, y_pred):
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)

    total = tp + fp + fn + tn
    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if tp == 0 and fn == 0 else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if tp == 0 and fp == 0 else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        'accuracy': round(accuracy, 4),
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'f1_score': round(f1, 4),
        'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
    }


def compute_average_precision(y_true_list, conf_list):
    """Compute Average Precision (AP) for a single class using 11-point interpolation."""
    combined = sorted(zip(conf_list, y_true_list), key=lambda x: -x[0])
    if not combined:
        return 0.0

    tp_cum = 0
    fp_cum = 0
    precisions = []
    recalls = []
    total_pos = sum(y_true_list)

    if total_pos == 0:
        return 0.0

    for _, yt in combined:
        if yt == 1:
            tp_cum += 1
        else:
            fp_cum += 1
        prec = tp_cum / (tp_cum + fp_cum) if (tp_cum + fp_cum) > 0 else 0.0
        rec = tp_cum / total_pos
        precisions.append(prec)
        recalls.append(rec)

    # 11-point interpolation
    ap = 0.0
    for t in np.arange(0.0, 1.1, 0.1):
        p_at_t = max([p for p, r in zip(precisions, recalls) if r >= t], default=0.0)
        ap += p_at_t / 11.0
    return round(ap, 4)


def run_evaluation(samples_dir):
    print("\n" + "=" * 65)
    print("  TRINETRA AI — Performance Evaluation (Real Images)")
    print("=" * 65)

    ground_truth = load_ground_truth(samples_dir)
    if not ground_truth:
        print("  ⚠ No ground truth data found.")
        return

    detector = LocateAnythingDetector()
    all_vtypes = set(ALL_VIOLATION_TYPES)
    violation_results = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0, 'tn': 0})
    per_image_results = []
    inference_times = []
    ap_data = {vtype: {'y_true': [], 'conf': []} for vtype in all_vtypes}

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
        vehicles = detector.filter_vehicles(detections)

        violations = []
        # Helmet detection uses ORIGINAL image (enhance_image damages helmet model)
        for v in check_helmet_violation(detections, img):
            violations.append(v)
        # All other detectors use processed (enhanced) image
        for v in check_triple_riding(detections, processed):
            violations.append(v)
        for v in check_seatbelt_violation(detections, processed):
            violations.append(v)
        for v in check_wrong_side_violation(detections, processed):
            violations.append(v)
        for v in check_red_light_violation(detections, processed):
            violations.append(v)
        for v in check_stop_line_violation(detections, processed):
            violations.append(v)

        if vehicles:
            reader = LicensePlateReader()
            # Use original image for OCR (like main.py)
            vehs_by_type = sorted(vehicles, key=lambda v: {2: 0, 5: 1, 7: 2, 3: 3}.get(v['class_id'], 9))
            for veh in vehs_by_type:
                text, conf = reader.read_plate(img, veh["bbox"])
                if text and conf >= 0.3:
                    break

        inference_time = (time.time() - t0) * 1000
        inference_times.append(inference_time)

        predicted_vtypes = set(v['violation_type'] for v in violations)
        predicted_with_conf = {v['violation_type']: v.get('confidence', 0.5) for v in violations}
        gt_vtypes = set(gt.get('violations', []))

        for vtype in all_vtypes:
            ap_data[vtype]['y_true'].append(1 if vtype in gt_vtypes else 0)
            ap_data[vtype]['conf'].append(predicted_with_conf.get(vtype, 0.0))
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
            'correct': predicted_vtypes == gt_vtypes,
        })

    print(f"\n{'─' * 65}")
    print(f"  Dataset: {len(per_image_results)} images evaluated")
    print(f"  Images with YOLO detections: {sum(1 for r in per_image_results if r['detection_count'] > 0)}")
    print(f"{'─' * 65}")

    print(f"\n  {'Per-Image Results':^61}")
    print(f"  {'─' * 61}")
    header = f"  {'Image':<35} {'Status':<10} {'Detections':<12} {'Time(ms)':<10}"
    print(header)
    print(f"  {'─' * 61}")
    correct_count = 0
    for r in per_image_results:
        status = "✓" if r['correct'] else "✗"
        if r['correct']:
            correct_count += 1
        det_str = str(r['detection_count']) if r['detection_count'] > 0 else '—'
        gt_str = f" GT:{r['gt']}" if r['gt'] else ""
        pred_str = f" PD:{r['predicted']}" if r['predicted'] else ""
        print(f"  {r['image']:<35} {status:<10} {det_str:<12} {r['inference_ms']:<10.1f}{gt_str}{pred_str}")

    print(f"\n  {'─' * 65}")
    print(f"  {'Overall Metrics':^61}")
    print(f"  {'─' * 65}")

    y_true_all = []
    y_pred_all = []
    for r in per_image_results:
        for vtype in all_vtypes:
            y_true_all.append(1 if vtype in r['gt'] else 0)
            y_pred_all.append(1 if vtype in r['predicted'] else 0)

    overall = compute_metrics(y_true_all, y_pred_all)
    print(f"  {'Test Accuracy':<25} {correct_count}/{len(per_image_results)} ({correct_count/len(per_image_results)*100:.1f}%)")
    for key in ['accuracy', 'precision', 'recall', 'f1_score']:
        print(f"  {key.replace('_', ' ').title():<25} {overall[key]:.4f}")

    print(f"\n  {'─' * 65}")
    print(f"  {'Per-Violation Metrics':^61}")
    print(f"  {'─' * 65}")
    any_violations_found = False
    for vtype in sorted(all_vtypes):
        r = violation_results[vtype]
        prec = r['tp'] / (r['tp'] + r['fp']) if (r['tp'] + r['fp']) > 0 else (1.0 if r['tp'] == 0 and r['fn'] == 0 else 0.0)
        rec = r['tp'] / (r['tp'] + r['fn']) if (r['tp'] + r['fn']) > 0 else (1.0 if r['tp'] == 0 and r['fp'] == 0 else 0.0)
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        if r['tp'] + r['fp'] + r['fn'] + r['tn'] > 0:
            any_violations_found = True
            print(f"  {vtype:<30} TP:{r['tp']} FP:{r['fp']} FN:{r['fn']} TN:{r['tn']}  "
                  f"Prec:{prec:.3f} Rec:{rec:.3f} F1:{f1:.3f}")

    if not any_violations_found:
        print(f"  {'(no violation test cases - all images were clean/negative)':^61}")

    print(f"\n  {'─' * 65}")
    print(f"  {'Mean Average Precision (mAP)':^61}")
    print(f"  {'─' * 65}")
    ap_scores = {}
    for vtype in sorted(all_vtypes):
        ap = compute_average_precision(ap_data[vtype]['y_true'], ap_data[vtype]['conf'])
        ap_scores[vtype] = ap
        print(f"  {vtype:<30} AP: {ap:.4f}")
    map_score = np.mean(list(ap_scores.values())) if ap_scores else 0.0
    print(f"  {'─' * 30}  {'─' * 10}")
    print(f"  {'mAP (all classes)':<30} {map_score:.4f}")

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

    detector = LocateAnythingDetector()
    reader = LicensePlateReader()

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
        'red_light_check': [],
        'stop_line_check': [],
        'plate_ocr': [],
    }

    for fname in image_files[:20]:
        path = os.path.join(samples_dir, fname)
        img = cv2.imread(path)
        if img is None:
            continue

        processed = enhance_image(img)

        t0 = time.time()
        detections = detector.detect(processed)
        stages['yolo_detection'].append((time.time() - t0) * 1000)

        t0 = time.time()
        # Helmet uses original image (not enhanced)
        check_helmet_violation(detections, img)
        stages['helmet_check'].append((time.time() - t0) * 1000)

        t0 = time.time()
        check_triple_riding(detections, processed)
        stages['triple_check'].append((time.time() - t0) * 1000)

        t0 = time.time()
        check_seatbelt_violation(detections, processed)
        stages['seatbelt_check'].append((time.time() - t0) * 1000)

        t0 = time.time()
        check_wrong_side_violation(detections, processed)
        stages['wrong_side_check'].append((time.time() - t0) * 1000)

        t0 = time.time()
        check_red_light_violation(detections, processed)
        stages['red_light_check'].append((time.time() - t0) * 1000)

        t0 = time.time()
        check_stop_line_violation(detections, processed)
        stages['stop_line_check'].append((time.time() - t0) * 1000)

        vehicles = detector.filter_vehicles(detections)
        t0 = time.time()
        if vehicles:
            vehs_by_type = sorted(vehicles, key=lambda v: {2: 0, 5: 1, 7: 2, 3: 3}.get(v['class_id'], 9))
            for veh in vehs_by_type:
                text, conf = reader.read_plate(img, veh["bbox"])
                if text and conf >= 0.3:
                    break
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
