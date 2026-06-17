import cv2
import numpy as np
import config


def _center_distance_score(person_bbox, motorcycle_bbox, img_shape):
    """Score based on distance between person center and motorcycle center.
    Closer = higher score. Normalized by image diagonal.
    """
    pcx = (person_bbox[0] + person_bbox[2]) / 2
    pcy = (person_bbox[1] + person_bbox[3]) / 2
    mcx = (motorcycle_bbox[0] + motorcycle_bbox[2]) / 2
    mcy = (motorcycle_bbox[1] + motorcycle_bbox[3]) / 2

    dist = np.sqrt((pcx - mcx) ** 2 + (pcy - mcy) ** 2)
    h, w = img_shape[:2] if img_shape and img_shape[0] else (480, 640)
    diag = np.sqrt(h ** 2 + w ** 2)
    # Score: 1.0 at distance 0, approaches 0 at distance = diag/3
    return max(0.0, 1.0 - (dist / (diag / 3)))


def _vertical_score(person_bbox, motorcycle_bbox):
    """Score based on vertical position. Person should be above motorcycle
    (sitting on seat). Higher when person center is above motorcycle center.
    """
    pcy = (person_bbox[1] + person_bbox[3]) / 2
    mcy = (motorcycle_bbox[1] + motorcycle_bbox[3]) / 2
    # Positive if person is above motorcycle center
    diff = mcy - pcy
    mh = motorcycle_bbox[3] - motorcycle_bbox[1]
    if mh <= 0:
        return 0.0
    # Normalize by motorcycle height: score 1.0 when person is ~1 height above
    normalized = diff / mh
    return max(0.0, min(1.0, normalized + 0.3))


def _horizontal_alignment_score(person_bbox, motorcycle_bbox):
    """Score based on horizontal alignment. Person should be centered over
    the motorcycle width. Score 1.0 when person center aligns with motorcycle center.
    """
    pcx = (person_bbox[0] + person_bbox[2]) / 2
    mcx = (motorcycle_bbox[0] + motorcycle_bbox[2]) / 2
    mw = motorcycle_bbox[2] - motorcycle_bbox[0]
    if mw <= 0:
        return 0.0
    offset = abs(pcx - mcx) / mw
    return max(0.0, 1.0 - offset)


def _overlap_score(person_bbox, motorcycle_bbox):
    """Optional bounding box overlap (IoU-based)."""
    x1 = max(person_bbox[0], motorcycle_bbox[0])
    y1 = max(person_bbox[1], motorcycle_bbox[1])
    x2 = min(person_bbox[2], motorcycle_bbox[2])
    y2 = min(person_bbox[3], motorcycle_bbox[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_p = (person_bbox[2] - person_bbox[0]) * (person_bbox[3] - person_bbox[1])
    area_m = (motorcycle_bbox[2] - motorcycle_bbox[0]) * (motorcycle_bbox[3] - motorcycle_bbox[1])
    union = area_p + area_m - inter
    if union <= 0:
        return 0.0
    return inter / union


def compute_rider_score(person_bbox, motorcycle_bbox, img_shape=(None, None)):
    """Compute overall association score between a person and a motorcycle.
    Score range: 0.0 (no association) to 1.0 (perfect association).
    """
    ds = _center_distance_score(person_bbox, motorcycle_bbox, img_shape)
    vs = _vertical_score(person_bbox, motorcycle_bbox)
    hs = _horizontal_alignment_score(person_bbox, motorcycle_bbox)
    os_ = _overlap_score(person_bbox, motorcycle_bbox)

    score = (
        config.RIDER_DISTANCE_WEIGHT * ds
        + config.RIDER_VERTICAL_WEIGHT * vs
        + config.RIDER_HORIZONTAL_WEIGHT * hs
        + config.RIDER_OVERLAP_WEIGHT * os_
    )
    return score, {'distance': ds, 'vertical': vs, 'horizontal': hs, 'overlap': os_}


def associate_riders(persons, motorcycles, img_shape=(None, None)):
    """Exclusive one-person-to-one-motorcycle assignment using scoring.

    Each person is assigned to the motorcycle with the highest score.
    A person is only assigned if the score exceeds a minimum threshold (0.15).

    Returns:
        List of dicts: {motorcycle, riders: [person, ...], rider_count, assignment_scores: {person_id: score}}
    """
    if not persons or not motorcycles:
        return [
            {'motorcycle': mc, 'riders': [], 'rider_count': 0, 'assignment_scores': {}}
            for mc in motorcycles
        ]

    # Build score matrix: for each person, compute score against each motorcycle
    person_scores = []
    for p in persons:
        best_score = 0.0
        best_mc_idx = -1
        best_details = {}
        for j, mc in enumerate(motorcycles):
            score, details = compute_rider_score(p['bbox'], mc['bbox'], img_shape)
            if score > best_score:
                best_score = score
                best_mc_idx = j
                best_details = details
        # Only assign if score exceeds minimum threshold
        if best_score >= 0.15 and best_mc_idx >= 0:
            person_scores.append({
                'person': p,
                'motorcycle_idx': best_mc_idx,
                'score': best_score,
                'details': best_details,
            })

    # Exclusive assignment: each motorcycle gets its assigned persons
    # (already exclusive since each person picks exactly one best motorcycle)
    results = []
    for j, mc in enumerate(motorcycles):
        riders = [ps['person'] for ps in person_scores if ps['motorcycle_idx'] == j]
        scores = {ps['person'].get('instance_id', f'p_{i}'): round(ps['score'], 3)
                  for i, ps in enumerate(person_scores) if ps['motorcycle_idx'] == j}

        total_confirmed = sum(1 for r in riders if r['confidence'] >= config.LOW_CONFIDENCE)
        total_possible = sum(1 for r in riders if r['confidence'] < config.LOW_CONFIDENCE)

        results.append({
            'motorcycle': mc,
            'riders': riders,
            'rider_count': len(riders),
            'confirmed_count': total_confirmed,
            'possible_count': total_possible,
            'assignment_scores': scores,
        })
    return results


def person_in_car_expanded(person_bbox, car_bbox, img_shape=(None, None)):
    """Check if person is inside car using scoring approach."""
    score, _ = compute_rider_score(person_bbox, car_bbox, img_shape)
    return score > 0.2


def _get_confidence_label(confidence):
    if confidence >= config.HIGH_CONFIDENCE:
        return 'high'
    if confidence >= config.MEDIUM_CONFIDENCE:
        return 'medium'
    if confidence >= config.LOW_CONFIDENCE:
        return 'low'
    return 'very_low'


def classify_occupancy(rider_count, association_confidence):
    """Classify occupancy with uncertainty model and estimated ranges.
    Never displays exact counts above 4.

    Returns:
        dict with: label, description, confidence_band, occupancy_estimate, needs_review
    """
    if rider_count == 0:
        return {'label': 'NO_OCCUPANTS', 'description': 'No riders detected',
                'confidence_band': 'high', 'occupancy_estimate': '0 occupants', 'needs_review': False}

    band = _get_confidence_label(association_confidence)

    if rider_count == 1:
        return {'label': 'NORMAL', 'description': '1 occupant',
                'confidence_band': band, 'occupancy_estimate': '1 occupant', 'needs_review': False}
    if rider_count == 2:
        return {'label': 'NORMAL', 'description': '2 occupants',
                'confidence_band': band, 'occupancy_estimate': '2 occupants', 'needs_review': False}

    needs_review = band in ('low', 'very_low') or rider_count >= 5

    if rider_count == 3:
        prefix = 'Confirmed' if band == 'high' else ('Likely' if band == 'medium' else 'Possible')
        lbl, desc = 'TRIPLE_RIDING', f'{prefix} triple riding — approximately 3 occupants'
        return {'label': lbl, 'description': desc,
                'confidence_band': band, 'occupancy_estimate': '3 occupants', 'needs_review': needs_review}

    if rider_count == 4:
        prefix = 'Confirmed' if band == 'high' else ('Likely' if band == 'medium' else 'Possible')
        lbl, desc = 'MOTORCYCLE_OVERLOADING', f'{prefix} motorcycle overloading — an estimated 4-5 occupants'
        return {'label': lbl, 'description': desc,
                'confidence_band': band, 'occupancy_estimate': '4-5 occupants', 'needs_review': needs_review}

    # rider_count >= 5
    prefix = 'Confirmed' if band == 'high' else ('Likely' if band == 'medium' else 'Possible')
    return {
        'label': 'MOTORCYCLE_EXTREME_OVERLOADING',
        'description': f'{prefix} extreme overloading — estimated 5+ occupants',
        'confidence_band': band,
        'occupancy_estimate': '5+ occupants',
        'needs_review': True,
    }


def draw_debug_association(image, persons, motorcycles, associations):
    """Draw debug visualization with association lines and confidence scores."""
    debug = image.copy()
    h, w = image.shape[:2]

    # Collect all assigned person IDs
    assigned_ids = set()
    rider_info = {}
    for assoc in associations:
        mc = assoc['motorcycle']
        mid = mc.get('instance_id', 'mc')
        mx1, my1, mx2, my2 = [int(v) for v in mc['bbox']]

        cv2.rectangle(debug, (mx1, my1), (mx2, my2), (255, 0, 0), 2)
        occ = classify_occupancy(assoc['rider_count'], 0.5)
        cv2.putText(debug, f"{mid}: {assoc['rider_count']} riders ({occ['confidence_band']})",
                    (mx1, my1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        for rider in assoc['riders']:
            rid = rider.get('instance_id', 'p')
            assigned_ids.add(id(rider))
            rx1, ry1, rx2, ry2 = [int(v) for v in rider['bbox']]
            cv2.rectangle(debug, (rx1, ry1), (rx2, ry2), (0, 0, 255), 2)
            cv2.putText(debug, f"{rid} {rider['confidence']:.2f}",
                        (rx1, ry1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

            # Association line
            mcx = (mx1 + mx2) // 2
            mcy = (my1 + my2) // 2
            pcx = (rx1 + rx2) // 2
            pcy = (ry1 + ry2) // 2
            cv2.line(debug, (mcx, mcy), (pcx, pcy), (0, 255, 255), 1)

            score = assoc.get('assignment_scores', {}).get(rid, 0)
            label_pt = ((mcx + pcx) // 2, (mcy + pcy) // 2 - 5)
            cv2.putText(debug, f"{score:.2f}", label_pt,
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

    # Non-associated persons in green
    for p in persons:
        if id(p) not in assigned_ids:
            rx1, ry1, rx2, ry2 = [int(v) for v in p['bbox']]
            cv2.rectangle(debug, (rx1, ry1), (rx2, ry2), (0, 255, 0), 2)
            cv2.putText(debug, f"{p.get('instance_id', 'p')} unassigned",
                        (rx1, ry1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

    cv2.putText(debug, "DEBUG: Blue=MC Red=Rider Green=Unassigned Yellow=Association",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    import os
    from datetime import datetime
    debug_path = os.path.join(config.DATA_DIR, f'debug_association_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg')
    cv2.imwrite(debug_path, debug)
    return debug_path
