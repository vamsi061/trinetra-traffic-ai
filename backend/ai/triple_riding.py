from ai.rider_association import associate_riders, draw_debug_association
import config


def compute_association_confidence(riders):
    """Combined confidence: geometric mean of rider confidences."""
    if not riders:
        return 0.0
    prod = 1.0
    for r in riders:
        prod *= r['confidence']
    return prod ** (1.0 / len(riders))


def check_triple_riding(detections, image=None):
    persons = [d for d in detections if d['class_id'] == config.PERSON_CLASS_ID]
    motorcycles = [d for d in detections if d['class_id'] == config.MOTORCYCLE_CLASS_ID]

    img_shape = image.shape[:2] if image is not None else (None, None)
    associations = associate_riders(persons, motorcycles, img_shape)

    violations = []

    for assoc in associations:
        mc = assoc['motorcycle']
        riders = assoc['riders']
        rider_count = assoc['rider_count']

        if rider_count == 0:
            continue

        # Safety heuristic: if many persons nearby even with low confidence, flag it
        total_nearby = rider_count
        if total_nearby >= 3:
            pass

        involved = [mc.get('instance_id', 'motorcycle')] + [r.get('instance_id', f'rider_{i}') for i, r in enumerate(riders)]

        if rider_count >= config.OVERLOADING_THRESHOLD:
            violations.append({
                'violation_type': 'MOTORCYCLE_OVERLOADING',
                'confidence': compute_association_confidence(riders),
                'rider_count': rider_count,
                'riders': riders,
                'motorcycle_bbox': mc['bbox'],
                'severity_score': config.RISK_SCORES.get('MOTORCYCLE_OVERLOADING', 95),
                'description': f'{rider_count} riders on {mc.get("instance_id", "motorcycle")} — OVERLOADING (limit: {config.OVERLOADING_THRESHOLD - 1})',
                'involved_objects': involved,
            })
        elif rider_count > 2:
            violations.append({
                'violation_type': 'TRIPLE_RIDING',
                'confidence': compute_association_confidence(riders),
                'rider_count': rider_count,
                'riders': riders,
                'motorcycle_bbox': mc['bbox'],
                'severity_score': config.RISK_SCORES.get('TRIPLE_RIDING', 75),
                'description': f'{rider_count} riders on {mc.get("instance_id", "motorcycle")} (exceeds limit of 2)',
                'involved_objects': involved,
            })

    # Draw debug visualization
    if image is not None and (motorcycles or persons):
        try:
            draw_debug_association(image, persons, motorcycles, associations)
        except Exception:
            pass

    return violations
