"""Download real-world traffic test images from COCO dataset.

Downloads curated images with motorcycles, cars, and persons
for testing the TRINETRA AI violation detection pipeline.

Usage:
    python download_real_dataset.py          # Download all images
    python download_real_dataset.py --verify # Verify YOLO detects objects
"""

import os, sys, json, time, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), 'samples')

# Ground truth labels for each test image
# Format: {filename: {violations: [violation_types], objects: [expected object types]}}
GROUND_TRUTH = {
    # === Motorcycle + Person images (for Helmet + Triple Riding) ===
    'real_moto_6.jpg': {
        'violations': [],  # 5 persons near 1 motorcycle - some may overlap
        'objects': ['motorcycle', 'person', 'person', 'person', 'person', 'person'],
    },
    'real_car_8.jpg': {
        'violations': [],
        'objects': ['motorcycle', 'person', 'person'],
    },
    # === Car images (for Seatbelt) ===
    'real_car_4.jpg': {
        'violations': [],
        'objects': ['car', 'car', 'car', 'person'],
    },
    'real_car_5.jpg': {
        'violations': [],
        'objects': ['car', 'car', 'person', 'person'],
    },
    # === Negative / No-violation images ===
    'real_moto_12.jpg': {
        'violations': [],
        'objects': [],
    },
    'real_moto_9.jpg': {
        'violations': [],
        'objects': [],
    },
}

# COCO images to download with known good detections
COCO_IMAGES = [
    # (image_id, filename, description)
    (393226, 'real_moto_6.jpg', '5 persons + 1 motorcycle'),
    (67616, 'real_car_8.jpg', '2 persons + 1 motorcycle'),
    (549390, 'real_car_4.jpg', '1 person + 3 cars + 1 truck'),
    (277005, 'real_car_5.jpg', '6 persons + 2 cars'),
]


def download_images(sample_dir=None):
    if sample_dir is None:
        sample_dir = SAMPLE_DIR
    os.makedirs(sample_dir, exist_ok=True)

    print(f"\nDownloading {len(COCO_IMAGES)} real test images...\n")
    import urllib.request

    count = 0
    for img_id, fname, desc in COCO_IMAGES:
        path = os.path.join(sample_dir, fname)
        if os.path.exists(path) and os.path.getsize(path) > 20000:
            print(f"  ✓ {fname} already exists ({desc})")
            count += 1
            continue

        url = f"http://images.cocodataset.org/val2017/000000{img_id}.jpg"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                if len(data) > 20000:
                    with open(path, 'wb') as f:
                        f.write(data)
                    count += 1
                    print(f"  ✓ {fname} ({len(data)//1024}KB) - {desc}")
                else:
                    print(f"  ✗ {fname} too small ({len(data)}B)")
        except Exception as e:
            print(f"  ✗ {fname}: {e}")
        time.sleep(0.5)

    print(f"\nDownloaded {count}/{len(COCO_IMAGES)} images")
    return count


def verify_detections(sample_dir=None):
    if sample_dir is None:
        sample_dir = SAMPLE_DIR

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    import cv2
    from ai.detector import ObjectDetector
    from utils.image_processing import enhance_image

    detector = ObjectDetector()
    print(f"\nVerifying YOLO detections on real images...\n")

    results = {}
    for fname, gt in sorted(GROUND_TRUTH.items()):
        path = os.path.join(sample_dir, fname)
        if not os.path.exists(path):
            print(f"  ⚠ {fname} not found")
            continue

        img = cv2.imread(path)
        processed = enhance_image(img)
        detections = detector.detect(processed)

        persons = len([d for d in detections if d['class_id'] == 0])
        motos = len([d for d in detections if d['class_id'] == 3])
        cars = len([d for d in detections if d['class_id'] == 2])
        labels = list(set(d['label'] for d in detections))

        has_yolo_detections = len(detections) > 0
        results[fname] = {
            'detections': len(detections),
            'persons': persons,
            'motorcycles': motos,
            'cars': cars,
            'labels': labels,
        }

        status = "✓" if has_yolo_detections else "→"
        print(f"  {status} {fname:<35} dets={len(detections):<2}  persons={persons}  motos={motos}  cars={cars}  {labels}")

    print(f"\nVerified {len(results)} images")
    return results


def save_ground_truth(sample_dir=None):
    if sample_dir is None:
        sample_dir = SAMPLE_DIR

    gt_path = os.path.join(sample_dir, 'ground_truth.json')
    with open(gt_path, 'w') as f:
        json.dump(GROUND_TRUTH, f, indent=2)
    print(f"\nGround truth saved to {gt_path}")
    print(f"  {len(GROUND_TRUTH)} test cases")
    for fname, gt in sorted(GROUND_TRUTH.items()):
        v_str = ', '.join(gt['violations']) if gt['violations'] else 'none'
        o_str = ', '.join(gt['objects']) if gt['objects'] else 'none'
        print(f"    {fname:<35} violations=[{v_str}]  objects=[{o_str}]")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true', help='Verify YOLO detections')
    parser.add_argument('--output', default=None, help='Custom output directory')
    args = parser.parse_args()

    if args.verify:
        verify_detections(args.output)
    else:
        download_images(args.output)
        verify_detections(args.output)
        save_ground_truth(args.output)
        print("\nDone! Run evaluation with: python evaluate.py")
