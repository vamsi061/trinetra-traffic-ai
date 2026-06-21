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


def _expanded_rider_count(motorcycle_bbox, all_persons, img_shape, crowded=False):
    """Count persons whose center falls inside an expanded MC bbox.
    
    Expands MC bbox by 25% horizontally and 30% vertically to catch
    riders that YOLO separates from the main MC detection (common in
    overloading where riders lean/sit in different positions).
    
    When crowded=True, uses tighter expansion to avoid counting
    pedestrians as riders.
    """
    mb = motorcycle_bbox
    mw = mb[2] - mb[0]
    mh = mb[3] - mb[1]
    if mw <= 0 or mh <= 0:
        return 0
    
    # Tighter expansion in crowded scenes to avoid counting pedestrians
    h_expand = 0.15 if crowded else 0.25
    v_expand_down = 0.20 if crowded else 0.30
    v_expand_up = 0.10 if crowded else 0.10
    
    ex = mb[0] - mw * h_expand
    ey = mb[1] - mh * v_expand_up
    ex2 = mb[2] + mw * h_expand
    ey2 = mb[3] + mh * v_expand_down  # extend downward
    
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

    # Compute crowded flag to avoid counting pedestrians as riders
    person_count = len(persons)
    mc_count = len(motorcycles)
    crowded = person_count >= 6 or (person_count >= 4 and mc_count >= 2)

    violations = []
    needs_review = False

    # Pre-compute expanded rider counts for each MC (with crowded awareness)
    expanded_counts = {}
    total_riders_across_all_mcs = 0
    for mc in motorcycles:
        ec = _expanded_rider_count(mc['bbox'], persons, img_shape, crowded=crowded)
        expanded_counts[mc.get('instance_id', '')] = ec

    for assoc in associations:
        mc = assoc['motorcycle']
        riders = assoc['riders']
        rider_count = assoc['rider_count']
        total_riders_across_all_mcs += rider_count

        if rider_count == 0:
            continue

        # In crowded scenes, only skip 1-2 rider MCs (3+ should still be flagged)
        if crowded and rider_count < 3:
            continue

        effective_count = rider_count
        mid = mc.get('instance_id', '')
        ec = expanded_counts.get(mid, 0)
        if ec > rider_count and rider_count >= 2:
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

    # Global check: if total riders across ALL MCs >= 3 but no single MC
    # triggered a violation, aggregate across motorcycles.
    # This handles cases where YOLO splits a single vehicle into multiple MC bboxes,
    # spreading riders across them (common in triple riding / overloading shots).
    # Only fires when there are more persons than MCs (avoids false positives
    # in scenes with many parked motorcycles near pedestrians).
    has_triple_or_overload = any(
        v['violation_type'] in ('TRIPLE_RIDING', 'MOTORCYCLE_OVERLOADING',
                                'MOTORCYCLE_EXTREME_OVERLOADING')
        for v in violations
    )
    if not has_triple_or_overload and total_riders_across_all_mcs >= 3 and len(persons) >= 3:
        global_expanded = sum(expanded_counts.get(m.get('instance_id', ''), 0) for m in motorcycles)
        final_count = max(total_riders_across_all_mcs, global_expanded)
        conf = 0.55  # lower confidence due to ambiguity
        occ = classify_occupancy(final_count, conf)
        violations.append({
            'violation_type': occ['label'],
            'confidence': round(conf, 2),
            'confidence_band': occ['confidence_band'],
            'rider_count': final_count,
            'confirmed_count': final_count,
            'possible_count': 0,
            'riders': [],
            'motorcycle_bbox': motorcycles[0]['bbox'] if motorcycles else [0, 0, 0, 0],
            'severity_score': compute_risk(config.RISK_SCORES.get(occ.get('label', 'TRIPLE_RIDING'), 75), conf),
            'description': f"{'Possible ' if occ['confidence_band'] == 'low' else ''}Multiple riders on vehicles in scene — aggregate {final_count} occupants detected",
            'involved_objects': [m.get('instance_id', 'motorcycle') for m in motorcycles],
            'needs_review': True,
        })

    # Draw debug visualization
    if image is not None and (motorcycles or persons):
        try:
            draw_debug_association(image, persons, motorcycles, associations)
        except Exception:
            pass

    return violations
