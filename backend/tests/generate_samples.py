"""Generate synthetic test images for TRINETRA AI testing.

Usage:
    python generate_samples.py                    # Generate all samples
    python generate_samples.py --show             # Show images (requires cv2 GUI)
    python generate_samples.py --output ./samples # Custom output dir
"""

import cv2
import numpy as np
import os
import argparse

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'samples')


def _save(name, img):
    path = os.path.join(OUTPUT_DIR, name)
    cv2.imwrite(path, img)
    print(f"  ✓ {name}  ({img.shape[1]}x{img.shape[0]})")
    return path


def draw_motorcycle(img, x, y, color=(80, 100, 200)):
    cv2.rectangle(img, (x, y), (x + 160, y + 100), color, -1)
    cv2.circle(img, (x + 20, y + 110), 18, (30, 30, 30), -1)
    cv2.circle(img, (x + 140, y + 110), 18, (30, 30, 30), -1)
    cv2.rectangle(img, (x + 60, y - 10), (x + 100, y), (40, 40, 40), -1)
    return img


def draw_person(img, x, y, color=(50, 80, 150)):
    cv2.rectangle(img, (x, y), (x + 30, y + 60), color, -1)
    cv2.circle(img, (x + 15, y - 5), 12, color, -1)
    return img


def draw_helmet(img, x, y):
    cv2.circle(img, (x + 15, y - 5), 14, (200, 200, 200), -1)
    cv2.circle(img, (x + 15, y - 5), 14, (100, 100, 100), 2)
    return img


def draw_plate(img, x, y, text="KA01AB1234"):
    import cv2
    h, w = 20, 60
    cv2.rectangle(img, (x, y), (x + w, y + h), (200, 200, 50), -1)
    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 0), 1)
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.35
    thickness = 1
    text_size = cv2.getTextSize(text, font, scale, thickness)[0]
    tx = x + (w - text_size[0]) // 2
    ty = y + h - 4
    cv2.putText(img, text, (tx, ty), font, scale, (0, 0, 0), thickness)
    return img


def generate_all(output_dir=None):
    if output_dir is None:
        output_dir = OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    print("\nGenerating TRINETRA AI test samples...\n")

    # ─── Test 1: Motorcycle + 1 rider + No Helmet ─────────────────
    img = np.ones((480, 640, 3), dtype=np.uint8) * 60
    img = draw_motorcycle(img, 200, 300)
    img = draw_person(img, 250, 230)
    img = draw_plate(img, 220, 410, "KA01AB1234")
    cv2.putText(img, "TEST1: NO HELMET", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 200), 2)
    _save("test1_no_helmet.jpg", img)

    # ─── Test 2: Motorcycle + 1 rider + Helmet ────────────────────
    img = np.ones((480, 640, 3), dtype=np.uint8) * 60
    img = draw_motorcycle(img, 200, 300)
    img = draw_person(img, 250, 230)
    img = draw_helmet(img, 250, 230)
    img = draw_plate(img, 220, 410, "MH12DE3456")
    cv2.putText(img, "TEST2: WITH HELMET", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 2)
    _save("test2_with_helmet.jpg", img)

    # ─── Test 3: Motorcycle + 3 riders (Triple Riding + No Helmet) ─
    img = np.ones((480, 640, 3), dtype=np.uint8) * 60
    img = draw_motorcycle(img, 180, 300)
    img = draw_person(img, 230, 230)
    img = draw_person(img, 260, 240)
    img = draw_person(img, 290, 250)
    img = draw_plate(img, 200, 410, "TN39XY7890")
    cv2.putText(img, "TEST3: TRIPLE RIDING", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 200), 2)
    _save("test3_triple_riding.jpg", img)

    # ─── Test 4: Car with visible plate ────────────────────────────
    img = np.ones((480, 640, 3), dtype=np.uint8) * 60
    cv2.rectangle(img, (150, 250), (450, 400), (120, 140, 220), -1)
    cv2.rectangle(img, (170, 260), (210, 300), (180, 200, 240), -1)
    cv2.rectangle(img, (390, 260), (430, 300), (180, 200, 240), -1)
    img = draw_plate(img, 260, 370, "DL04PQ1234")
    cv2.putText(img, "TEST4: CAR + PLATE", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 2)
    _save("test4_car_plate.jpg", img)

    # ─── Test 5: Empty road (no violations) ─────────────────────────
    img = np.ones((480, 640, 3), dtype=np.uint8) * 60
    img = draw_motorcycle(img, 200, 300)
    img = draw_person(img, 250, 230)
    img = draw_helmet(img, 250, 230)
    img = draw_person(img, 280, 240)
    img = draw_helmet(img, 280, 240)
    cv2.putText(img, "TEST5: 2 RIDERS BOTH HELMETS", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 0), 2)
    _save("test5_compliant.jpg", img)

    # ─── Test 6: No motorcycle (just people) ───────────────────────
    img = np.ones((480, 640, 3), dtype=np.uint8) * 60
    draw_person(img, 200, 250)
    draw_person(img, 300, 260)
    cv2.putText(img, "TEST6: NO VEHICLE", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 2)
    _save("test6_no_vehicle.jpg", img)

    print(f"\nAll samples generated in: {output_dir}")
    return output_dir


def show_samples(output_dir):
    for f in sorted(os.listdir(output_dir)):
        if f.endswith(('.jpg', '.png')):
            path = os.path.join(output_dir, f)
            img = cv2.imread(path)
            cv2.imshow(f, img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default=OUTPUT_DIR)
    parser.add_argument('--show', action='store_true')
    args = parser.parse_args()
    out = generate_all(args.output)
    if args.show:
        show_samples(out)
