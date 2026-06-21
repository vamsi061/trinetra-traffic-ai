from ai.rider_association import associate_riders, draw_debug_association, classify_occupancy
import config


def compute_association_confidence(riders):
    """Combined confidence: mean of rider confidences weighted by assignment score."""
    if not riders:
        return 0.0
    return sum(r['confidence'] for r in riders) / len(riders)


def compute_risk(base_score, confidence):
    """Confidence-adjusted risk score."""
    return round(base_score * min(confidence + 0.2, 1.0), 1)


def get_violation_label(occ_label):
    """Map occupancy label to violation type."""
    mapping = {
        'TRIPLE_RIDING': 'TRIPLE_RIDING',
        'MOTORCYCLE_OVERLOADING': 'MOTORCYCLE_OVERLOADING',
        'MOTORCYCLE_EXTREME_OVERLOADING': 'MOTORCYCLE_EXTREME_OVERLOADING',
    }
    return mapping.get(occ_label)


def _expanded_rider_count(motorcycle_bbox, all_persons, img_shape):
    """Count persons whose center falls inside an expanded MC bbox.
    
    Expands MC bbox by 25% horizontally and 10% vertically to catch
    riders that YOLO separates from the main MC detection (common in
    overloading where riders lean/sit in different positions).
    """
    mb = motorcycle_bbox
    mw = mb[2] - mb[0]
    mh = mb[3] - mb[1]
    if mw <= 0 or mh <= 0:
        return 0
    
    ex = mb[0] - mw * 0.25
    ey = mb[1] - mh * 0.1
    ex2 = mb[2] + mw * 0.25
    ey2 = mb[3] + mh * 0.5  # extend more downward (riders sit above seat)
    
    # Clamp to image bounds
    h, w = img_shape[:2] if img_shape else (1000, 1000)
    ex, ey = max(0, ex), max(0, ey)
    ex2, ey2 = min(w, ex2), min(h, ey2)
    
    count = 0
    for p in all_persons:
        pcx = (p['bbox'][0] + p['bbox'][2]) / 2
        pcy = (p['bbox'][1] + p['bbox'][3]) / 2
        if ex <= pcx <= ex2 and ey <= pcy <= ey2:
            count += 1
    return count


def check_triple_riding(detections, image=None):
    persons = [d for d in detections if d['class_id'] == config.PERSON_CLASS_ID]
    motorcycles = [d for d in detections if d['class_id'] == config.MOTORCYCLE_CLASS_ID]

    img_shape = image.shape[:2] if image is not None else (None, None)
    associations = associate_riders(persons, motorcycles, img_shape)

    violations = []
    needs_review = False

    # Pre-compute expanded rider counts for each MC
    expanded_counts = {}
    for mc in motorcycles:
        ec = _expanded_rider_count(mc['bbox'], persons, img_shape)
        expanded_counts[mc.get('instance_id', '')] = ec

    for assoc in associations:
        mc = assoc['motorcycle']
        riders = assoc['riders']
        rider_count = assoc['rider_count']

        if rider_count == 0:
            continue

        # Use expanded count if it's higher (catches overloading where
        # YOLO splits rider detections across separate bboxes).
        # Only activate when the MC already has confirmed riders (>= 3)
        # to avoid counting pedestrians as riders.
        effective_count = rider_count
        mid = mc.get('instance_id', '')
        ec = expanded_counts.get(mid, 0)
        if ec > rider_count and rider_count >= 3:
            effective_count = ec

        conf = compute_association_confidence(riders)
        occ = classify_occupancy(effective_count, conf)

        if occ['needs_review']:
            needs_review = True

        involved = [mc.get('instance_id', 'motorcycle')] + [r.get('instance_id', f'rider_{i}') for i, r in enumerate(riders)]
        base_score = config.RISK_SCORES.get(get_violation_label(occ['label']), 0)

        prefix = ''
        if occ['confidence_band'] == 'low':
            prefix = 'Possible '
        elif occ['confidence_band'] == 'medium':
            prefix = 'Likely '

        violations.append({
            'violation_type': occ['label'],
            'confidence': round(conf, 3),
            'confidence_band': occ['confidence_band'],
            'rider_count': effective_count,
            'confirmed_count': assoc.get('confirmed_count', rider_count),
            'possible_count': max(assoc.get('possible_count', 0), effective_count - rider_count),
            'riders': riders,
            'motorcycle_bbox': mc['bbox'],
            'severity_score': compute_risk(base_score, conf),
            'description': f"{prefix}{occ['description']} on {mc.get('instance_id', 'motorcycle')}",
            'involved_objects': involved,
            'needs_review': occ['needs_review'],
        })

    # Draw debug visualization
    if image is not None and (motorcycles or persons):
        try:
            draw_debug_association(image, persons, motorcycles, associations)
        except Exception:
            pass

    return violations
