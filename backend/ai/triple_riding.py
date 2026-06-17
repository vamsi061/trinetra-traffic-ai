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


def check_triple_riding(detections, image=None):
    persons = [d for d in detections if d['class_id'] == config.PERSON_CLASS_ID]
    motorcycles = [d for d in detections if d['class_id'] == config.MOTORCYCLE_CLASS_ID]

    img_shape = image.shape[:2] if image is not None else (None, None)
    associations = associate_riders(persons, motorcycles, img_shape)

    violations = []
    needs_review = False

    for assoc in associations:
        mc = assoc['motorcycle']
        riders = assoc['riders']
        rider_count = assoc['rider_count']

        if rider_count == 0:
            continue

        conf = compute_association_confidence(riders)
        occ = classify_occupancy(rider_count, conf)

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
            'rider_count': rider_count,
            'confirmed_count': assoc.get('confirmed_count', rider_count),
            'possible_count': assoc.get('possible_count', 0),
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
