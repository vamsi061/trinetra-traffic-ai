import cv2
import numpy as np
import os
from datetime import datetime
import config

VIOLATION_COLORS = {
    'NO_HELMET': (0, 0, 255),
    'TRIPLE_RIDING': (255, 100, 150),
    'MOTORCYCLE_OVERLOADING': (255, 50, 100),
    'MOTORCYCLE_EXTREME_OVERLOADING': (200, 0, 50),
    'POSSIBLE_ILLEGAL_PARKING': (255, 200, 0),
    'SEATBELT_VIOLATION': (255, 165, 0),
    'WRONG_SIDE_DRIVING': (255, 0, 255),
    'RED_LIGHT_VIOLATION': (255, 0, 0),
    'STOP_LINE_VIOLATION': (128, 0, 128),
}

DETECTION_COLORS = {
    'person': (0, 200, 0),
    'motorcycle': (200, 100, 0),
    'car': (0, 100, 200),
    'bus': (0, 200, 200),
    'truck': (200, 0, 200),
    'traffic light': (0, 255, 255),
    'stop sign': (255, 200, 0),
}

CALLOUT_BG = (20, 20, 20)


def _draw_label_bg(img, text, org, font, scale, color, thickness=2, padding=4):
    """Draw text with filled background rectangle for readability."""
    (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
    x, y = org
    cv2.rectangle(img, (x - padding, y - th - padding), (x + tw + padding, y + padding), CALLOUT_BG, -1)
    cv2.putText(img, text, (x, y - 2), font, scale, color, thickness)


def _draw_callout_circle(img, cx, cy, number, color):
    """Draw a numbered callout circle (①②③) at given position."""
    radius = 16
    # Outer circle
    cv2.circle(img, (cx, cy), radius, color, -1)
    cv2.circle(img, (cx, cy), radius, (255, 255, 255), 2)
    # Number
    cv2.putText(img, str(number), (cx - 7, cy + 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)


def _draw_halo(img, bbox, color, alpha=0.25):
    """Draw a semi-transparent halo (glow) around a bounding box."""
    x1, y1, x2, y2 = [int(v) for v in bbox]
    overlay = img.copy()
    padding = 8
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(img.shape[1], x2 + padding)
    y2 = min(img.shape[0], y2 + padding)
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)


def _get_bbox_from_violation(v):
    """Extract the primary bbox from a violation dict, returns (bbox, label)."""
    for key in ('vehicle_bbox', 'motorcycle_bbox', 'person_bbox'):
        if key in v:
            return v[key], key
    return None, None


def _get_vehicle_instance(v):
    """Get the best vehicle/person instance label for this violation."""
    involved = v.get('involved_objects', [])
    if involved:
        return involved[0]
    desc = v.get('description', '')
    if ' ' in desc:
        return desc.split(' ')[0]
    return ''


VIOLATION_SHORT = {
    'NO_HELMET': 'No Helmet',
    'TRIPLE_RIDING': 'Triple Riding',
    'MOTORCYCLE_OVERLOADING': 'Overloading',
    'MOTORCYCLE_EXTREME_OVERLOADING': 'Extreme Overload',
    'POSSIBLE_ILLEGAL_PARKING': 'Illegal Parking',
    'SEATBELT_VIOLATION': 'No Seatbelt',
    'WRONG_SIDE_DRIVING': 'Wrong Side',
    'RED_LIGHT_VIOLATION': 'Red Light',
    'STOP_LINE_VIOLATION': 'Stop Line',
}


def generate_evidence(original_image, detections, violations, plate_info, source_filename="image"):
    image = original_image.copy()
    height, width = image.shape[:2]

    # ── Step 1: Draw all detection bboxes ──
    for det in detections:
        x1, y1, x2, y2 = [int(v) for v in det['bbox']]
        label = det.get('label', 'unknown')
        instance_id = det.get('instance_id', label)
        color = DETECTION_COLORS.get(label, (200, 200, 200))
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 1)
        _draw_label_bg(image, f"{instance_id} {det['confidence']:.2f}",
                       (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    # ── Step 2: Assign callout numbers to unique violations ──
    # Each unique (violation_type, primary_instance_id) gets its own number
    callout_map = {}  # (vtype, instance_id) -> number
    numbered_violations = []
    for v in violations:
        vtype = v['violation_type']
        inst = _get_vehicle_instance(v)
        key = (vtype, inst)
        if key not in callout_map:
            callout_map[key] = len(callout_map) + 1
        numbered_violations.append((v, callout_map[key]))

    # ── Step 3: Draw halos and callout markers ──
    for v, num in numbered_violations:
        vtype = v['violation_type']
        color = VIOLATION_COLORS.get(vtype, (255, 255, 255))
        bbox, bbox_type = _get_bbox_from_violation(v)

        if bbox:
            x1, y1, x2, y2 = [int(x) for x in bbox]
            # Halo effect
            _draw_halo(image, bbox, color, alpha=0.18)
            # Thick colored border
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 3)

            # Callout circle at bottom-center of bbox (avoids overlapping with top banner)
            cx = (x1 + x2) // 2
            cy = min(height - 14, y2 + 14)
            _draw_callout_circle(image, cx, cy, num, color)

        # Draw rider markers for triple riding
        for rider in v.get('riders', []):
            rx1, ry1, rx2, ry2 = [int(r) for r in rider['bbox']]
            cv2.rectangle(image, (rx1, ry1), (rx2, ry2), (0, 165, 255), 2)
            _draw_label_bg(image, 'RIDER', (rx1, ry1 - 8),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)

    # ── Step 4: Draw violation labels on each violating bbox ──
    # Group violations by bbox key to stagger overlapping banners
    bbox_groups = {}
    for v, num in numbered_violations:
        bbox, _ = _get_bbox_from_violation(v)
        if not bbox:
            continue
        key = tuple(int(x) for x in bbox)
        bbox_groups.setdefault(key, []).append((v, num))

    for bbox_key, vnums in bbox_groups.items():
        x1, y1, x2, y2 = bbox_key
        for offset_idx, (v, num) in enumerate(vnums):
            vtype = v['violation_type']
            color = VIOLATION_COLORS.get(vtype, (255, 255, 255))
            short = VIOLATION_SHORT.get(vtype, vtype)

            label_w = 180
            label_h = 22
            stagger = offset_idx * (label_h + 2)
            banner_x1 = max(0, x1)
            banner_y1 = max(0, y1 - label_h - 4 - stagger)
            banner_x2 = min(width, x1 + label_w)
            banner_y2 = max(0, y1 - 4 - stagger)
            cv2.rectangle(image, (banner_x1, banner_y1), (banner_x2, banner_y2), CALLOUT_BG, -1)
            cv2.rectangle(image, (banner_x1, banner_y1), (banner_x2, banner_y2), color, 1)
            cv2.putText(image, f"#{num} {short}", (banner_x1 + 4, banner_y2 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

    # ── Step 5: Draw special scene markers ──
    # Draw stop line if detected (from stop_line_violation context)
    for v in violations:
        if v['violation_type'] == 'STOP_LINE_VIOLATION' and 'stop_line_y' in v:
            sl_y = int(v['stop_line_y'])
            cv2.line(image, (0, sl_y), (width, sl_y), VIOLATION_COLORS['STOP_LINE_VIOLATION'], 3)
            cv2.putText(image, 'STOP LINE', (10, sl_y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, VIOLATION_COLORS['STOP_LINE_VIOLATION'], 2)

        if v['violation_type'] == 'RED_LIGHT_VIOLATION' and 'traffic_light_bbox' in v:
            tx1, ty1, tx2, ty2 = [int(t) for t in v['traffic_light_bbox']]
            cv2.rectangle(image, (tx1, ty1), (tx2, ty2), VIOLATION_COLORS['RED_LIGHT_VIOLATION'], 3)
            cv2.putText(image, 'RED LIGHT', (tx1, max(14, ty1 - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, VIOLATION_COLORS['RED_LIGHT_VIOLATION'], 2)

    # ── Step 6: Header bar ──
    cv2.rectangle(image, (0, 0), (width, 42), CALLOUT_BG, -1)
    cv2.putText(image, "TRINETRA AI — Traffic Enforcement Intelligence",
                (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.putText(image, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                (width - 180, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

    # ── Step 7: Violation legend (top-right) ──
    uniq = {}
    for v, num in numbered_violations:
        vtype = v['violation_type']
        inst = _get_vehicle_instance(v)
        if num not in uniq:
            uniq[num] = (vtype, inst)

    legend_x = width - 260
    legend_y = 50
    legend_w = 248
    item_h = 20
    header_h = 22
    total_h = header_h + len(uniq) * item_h + 12

    cv2.rectangle(image, (legend_x, legend_y), (legend_x + legend_w, legend_y + total_h), CALLOUT_BG, -1)
    cv2.rectangle(image, (legend_x, legend_y), (legend_x + legend_w, legend_y + total_h), (80, 80, 80), 1)
    cv2.putText(image, "VIOLATIONS", (legend_x + 8, legend_y + 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    for idx, (num, (vtype, inst)) in enumerate(sorted(uniq.items())):
        color = VIOLATION_COLORS.get(vtype, (255, 255, 255))
        y = legend_y + header_h + 4 + idx * item_h
        # Small color swatch
        cv2.circle(image, (legend_x + 14, y + 7), 6, color, -1)
        cv2.circle(image, (legend_x + 14, y + 7), 6, (255, 255, 255), 1)
        # Callout number
        cv2.putText(image, str(num), (legend_x + 28, y + 11),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        short = VIOLATION_SHORT.get(vtype, vtype)
        label = f"{short} — {inst}" if inst else short
        cv2.putText(image, label, (legend_x + 44, y + 11),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    # ── Step 8: Footer summary bar ──
    vtype_counts = {}
    for v in violations:
        vt = v['violation_type']
        vtype_counts[vt] = vtype_counts.get(vt, 0) + 1

    footer_y = height - 28
    cv2.rectangle(image, (0, footer_y), (width, height), CALLOUT_BG, -1)
    parts = [f"{VIOLATION_SHORT.get(t, t)}: {c}" for t, c in sorted(vtype_counts.items())]
    footer_text = "  |  ".join(parts) if parts else "No violations detected"
    cv2.putText(image, footer_text, (12, footer_y + 19),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    # ── Step 9: Plate overlay (bottom-left, above footer) ──
    if plate_info and plate_info[0]:
        plate_text, plate_conf = plate_info
        plate_y = footer_y - 10
        _draw_label_bg(image, f"Plate: {plate_text} ({plate_conf:.0%})",
                       (12, plate_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    source_basename = os.path.splitext(os.path.basename(source_filename))[0]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    evidence_path = os.path.join(config.EVIDENCE_DIR, f'{source_basename}_evidence_{timestamp}.jpg')
    cv2.imwrite(evidence_path, image)
    return evidence_path
