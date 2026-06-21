"""Violation Prioritization & False Positive Suppression for TRINETRA AI.

Pipeline:
  1. validate_violation_context — reject violations missing required scene evidence
  2. calculate_evidence_score — rate each violation's evidential support
  3. apply_confidence_threshold — <0.50 discard, 0.50-0.70 → Possible, >0.70 → Violation
  4. rank_violations — by scene relevance + confidence + context score
  5. select_primary — highest-ranked violation becomes the Primary Finding
  6. suppress_secondary — hide low-scoring secondary violations behind review flag
"""

import logging

logger = logging.getLogger(__name__)

# Minimum evidence thresholds per violation type
EVIDENCE_THRESHOLD = 0.50
CONFIDENCE_FLOOR = 0.50
POSSIBLE_CEILING = 0.70

# Scene relevance keywords: maps violation type → Florence-2 narrative triggers
SCENE_KEYWORDS = {
    'POSSIBLE_ILLEGAL_PARKING': ['parked', 'parking', 'stationary', 'stopped',
                                  'curb', 'kerb', 'footpath', 'roadside',
                                  'no parking', 'parking zone', 'restricted'],
    'NO_HELMET': ['helmet', 'rider', 'motorcycle', 'scooter', 'without helmet',
                  'no helmet'],
    'SEATBELT_VIOLATION': ['seatbelt', 'seat belt', 'car', 'driver', 'occupant',
                           'cabin', 'windscreen'],
    'TRIPLE_RIDING': ['triple', 'three', 'three people', 'three persons',
                      'overloaded', 'overloading'],
    'STOP_LINE_VIOLATION': ['stop line', 'stop', 'halt', 'crossed', 'intersection'],
    'WRONG_SIDE_DRIVING': ['wrong side', 'wrong-way', 'oncoming', 'opposite'],
    'RED_LIGHT_VIOLATION': ['red light', 'signal', 'traffic light'],
}

# Context prerequisites: what must exist in detections for each violation type
#   all_of: every label must be present (AND)
#   any_of: at least one label must be present (OR)
CONTEXT_REQUIREMENTS = {
    'POSSIBLE_ILLEGAL_PARKING': {'any_of': ['car', 'motorcycle', 'truck', 'bus', 'person']},
    'NO_HELMET': {'all_of': ['motorcycle', 'person']},
    'SEATBELT_VIOLATION': {'all_of': ['car', 'person']},
    'TRIPLE_RIDING': {'all_of': ['motorcycle', 'person']},
    'STOP_LINE_VIOLATION': {},
    'WRONG_SIDE_DRIVING': {},
    'RED_LIGHT_VIOLATION': {'any_of': ['traffic light', 'car', 'motorcycle']},
    'MOTORCYCLE_OVERLOADING': {'all_of': ['motorcycle', 'person']},
    'MOTORCYCLE_EXTREME_OVERLOADING': {'all_of': ['motorcycle', 'person']},
}

# Evidence factor weights
EVIDENCE_WEIGHTS = {
    'POSSIBLE_ILLEGAL_PARKING': {
        'has_parking_context': 0.40,
        'vehicle_large_enough': 0.25,
        'scene_mentions_parking': 0.20,
        'not_moving': 0.15,
    },
    'NO_HELMET': {
        'has_motorcycle': 0.30,
        'has_person': 0.30,
        'model_available': 0.25,
        'scene_mentions_rider': 0.15,
    },
    'SEATBELT_VIOLATION': {
        'has_car': 0.35,
        'person_in_car': 0.35,
        'cabin_visible': 0.20,
        'scene_mentions_car': 0.10,
    },
    'TRIPLE_RIDING': {
        'has_motorcycle': 0.30,
        'rider_count_ge_3': 0.40,
        'scene_mentions_overload': 0.15,
        'association_confidence': 0.15,
    },
    'STOP_LINE_VIOLATION': {
        'stop_line_detected': 0.40,
        'vehicle_past_line': 0.35,
        'scene_mentions_stop': 0.25,
    },
}


def _scene_relevance_boost(violation_type, narrative):
    """Calculate scene relevance boost (0.0–0.25) from Florence-2 narrative."""
    if not narrative:
        return 0.0
    narrative_lower = narrative.lower()
    keywords = SCENE_KEYWORDS.get(violation_type, [])
    if not keywords:
        return 0.0
    matches = sum(1 for kw in keywords if kw in narrative_lower)
    if matches == 0:
        return 0.0
    return min(0.25, matches * 0.08)


def _evidence_factors(violation, detections, scene_info):
    """Calculate evidence score components for a violation."""
    vtype = violation['violation_type']
    weights = EVIDENCE_WEIGHTS.get(vtype, {})
    score = 0.0
    factors = {}
    labels = [d['label'] for d in detections]

    if vtype == 'POSSIBLE_ILLEGAL_PARKING':
        parking_context = violation.get('description', '')
        has_context = any(kw in parking_context.lower()
                          for kw in ['parking', 'parked', 'roadside', 'footpath', 'curb', 'lane'])
        factors['has_parking_context'] = 1.0 if has_context else 0.0
        factors['vehicle_large_enough'] = 0.8  # already passed size filter
        factors['scene_mentions_parking'] = 0.5 if _scene_relevance_boost(vtype, scene_info.get('narrative')) > 0 else 0.0
        factors['not_moving'] = 1.0  # parking detector already filters moving

    elif vtype == 'SEATBELT_VIOLATION':
        has_car = 'car' in labels
        has_person = 'person' in labels
        factors['has_car'] = 1.0 if has_car else 0.0
        factors['person_in_car'] = 1.0 if violation.get('person_bbox') and violation.get('vehicle_bbox') else 0.0
        factors['cabin_visible'] = 0.5  # proxy: no direct cabin detection
        factors['scene_mentions_car'] = 0.5 if _scene_relevance_boost(vtype, scene_info.get('narrative')) > 0 else 0.0

    elif vtype == 'NO_HELMET':
        has_mc = 'motorcycle' in labels
        has_person = 'person' in labels
        factors['has_motorcycle'] = 1.0 if has_mc else 0.0
        factors['has_person'] = 1.0 if has_person else 0.0
        model_avail = violation.get('helmet_state') != 'HELMET_UNKNOWN'
        factors['model_available'] = 1.0 if model_avail else 0.0
        factors['scene_mentions_rider'] = 0.5 if _scene_relevance_boost(vtype, scene_info.get('narrative')) > 0 else 0.0

    elif vtype == 'TRIPLE_RIDING':
        rider_count = violation.get('rider_count', 0)
        factors['has_motorcycle'] = 1.0 if 'motorcycle' in labels else 0.0
        factors['rider_count_ge_3'] = 1.0 if rider_count >= 3 else 0.0
        factors['scene_mentions_overload'] = 0.5 if _scene_relevance_boost(vtype, scene_info.get('narrative')) > 0 else 0.0
        factors['association_confidence'] = min(1.0, violation.get('confidence', 0))

    elif vtype == 'STOP_LINE_VIOLATION':
        factors['stop_line_detected'] = 1.0 if violation.get('stop_line_y') else 0.0
        factors['vehicle_past_line'] = 0.7  # already passed geometric check
        factors['scene_mentions_stop'] = 0.5 if _scene_relevance_boost(vtype, scene_info.get('narrative')) > 0 else 0.0

    else:
        factors['default'] = 0.5

    for key, weight in weights.items():
        val = factors.get(key, 0.5)
        score += val * weight

    return min(1.0, score), factors


def validate_violation_context(violation, detections):
    """Reject violations missing required scene evidence.

    Checks both `all_of` (every label required) and `any_of` (at least one).

    Returns:
        (valid: bool, reason: str)
    """
    vtype = violation['violation_type']
    reqs = CONTEXT_REQUIREMENTS.get(vtype)
    if not reqs:
        return True, ''

    labels = [d['label'] for d in detections]

    all_of = reqs.get('all_of', [])
    any_of = reqs.get('any_of', [])

    for label in all_of:
        if label not in labels:
            return False, f'Required detection "{label}" not present in scene'

    if any_of:
        found = any(label in labels for label in any_of)
        if not found:
            return False, f'None of required detections {any_of} present in scene'

    return True, ''


def apply_threshold(violation):
    """Apply confidence and evidence thresholds.

    Rules:
      - Raw confidence < 0.50 → discard (unreliable detection)
      - Evidence score < 0.30 → discard (no scene evidence supports this)
      - Raw confidence 0.50–0.70 → 'Possible Violation', needs review
      - Raw confidence > 0.70 → confirmed violation
      - Evidence score 0.30–0.60 + confirmed → still flagged needs_review

    Returns:
        (action: str, display_type: str, needs_review: bool)
        action is one of: 'discard', 'possible', 'confirmed'
    """
    raw_conf = violation.get('confidence', 0)
    evidence = violation.get('_evidence_score', 1.0)

    if raw_conf < CONFIDENCE_FLOOR:
        return 'discard', '', False

    if evidence < 0.30:
        return 'discard', '', False

    vtype = violation.get('display_type', violation['violation_type'].replace('_', ' ').title())

    if raw_conf < POSSIBLE_CEILING:
        display = f'Possible {vtype}' if not vtype.startswith('Possible ') else vtype
        return 'possible', display, True

    needs_review = evidence < 0.60
    return 'confirmed', vtype, needs_review


def rank_violations(violations, scene_info, detections):
    """Rank violations by combined score.

    Score = confidence * 0.40 + evidence_score * 0.35 + scene_relevance * 0.25

    Returns:
        list of (score, violation) sorted descending
    """
    ranked = []
    narrative = scene_info.get('narrative', '') if scene_info else ''

    for v in violations:
        raw_conf = v.get('confidence', 0)
        evidence_score, factors = _evidence_factors(v, detections, scene_info)
        v['_evidence_score'] = evidence_score
        v['_evidence_factors'] = factors
        scene_boost = _scene_relevance_boost(v['violation_type'], narrative)

        combined = (raw_conf * 0.40) + (evidence_score * 0.35) + (scene_boost * 0.25)
        v['_priority_score'] = round(combined, 3)
        ranked.append((combined, v))

    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked


def select_primary(violations, scene_info, detections):
    """Main pipeline: filter, score, rank, and select primary violation.

    Args:
        violations: list of raw violation dicts
        scene_info: dict with narrative, scene_breakdown
        detections: list of detection dicts

    Returns:
        tuple of (processed_violations, primary_finding)
        - processed_violations: filtered and enriched violation list
        - primary_finding: dict with type, confidence, reason, or None
    """
    if not violations:
        return [], None

    # Step 1: Context validation & evidence scoring
    valid_violations = []
    for v in violations:
        valid, reason = validate_violation_context(v, detections)
        if not valid:
            logger.debug(f'Rejected {v.get("violation_type")}: {reason}')
            continue
        valid_violations.append(v)

    if not valid_violations:
        return [], None

    # Step 2: Evidence scoring
    for v in valid_violations:
        evidence_score, factors = _evidence_factors(v, detections, scene_info)
        v['_evidence_score'] = evidence_score
        v['_evidence_factors'] = factors

    # Step 3: Apply thresholds
    passed = []
    for v in valid_violations:
        action, display, needs_review = apply_threshold(v)
        if action == 'discard':
            logger.debug(f'Discarded {v.get("violation_type")} (conf={v.get("confidence"):.2f}, evidence={v.get("_evidence_score", 0):.2f})')
            continue
        v['display_type'] = display
        v['needs_review'] = needs_review or v.get('needs_review', False)
        if action == 'possible':
            v['human_review_status'] = 'manual_verification_required'
        passed.append(v)

    if not passed:
        return [], None

    # Step 4: Rank by priority score
    ranked = rank_violations(passed, scene_info, detections)

    # Step 5: Select primary (highest ranked)
    top_score, primary = ranked[0]
    primary['_is_primary'] = True
    vtype = primary['violation_type']
    narrative = scene_info.get('narrative', '') if scene_info else ''
    scene_boost = _scene_relevance_boost(vtype, narrative)

    reason_parts = []
    if scene_boost > 0:
        vtype_clean = vtype.lower().replace('_', ' ')
        reason_parts.append(f'Scene analysis indicates {vtype_clean}')
    if primary.get('description'):
        reason_parts.append(primary['description'])
    elif primary.get('_evidence_factors'):
        top_factors = sorted(primary['_evidence_factors'].items(), key=lambda x: x[1], reverse=True)[:2]
        for k, v in top_factors:
            if v > 0.5:
                k_clean = k.replace('_', ' ').title()
                reason_parts.append(f'{k_clean} confirmed')

    primary_finding = {
        'type': primary.get('display_type', primary['violation_type'].replace('_', ' ').title()),
        'violation_type': vtype,
        'confidence': round(primary['confidence'], 3),
        'evidence_score': round(primary.get('_evidence_score', 0), 3),
        'priority_score': round(primary.get('_priority_score', 0), 3),
        'reason': '; '.join(reason_parts) if reason_parts else 'Highest priority violation in scene',
        'needs_review': primary.get('needs_review', False),
        'enforcement_recommendation': primary.get('enforcement_recommendation', 'Officer review recommended.'),
    }

    # Step 6: Suppress low-confidence secondary violations
    processed = []
    for _, v in ranked:
        if v.get('_is_primary'):
            processed.append(v)
            continue
        # For secondary violations, if evidence < threshold, mark as suppressed
        if v.get('_evidence_score', 0) < EVIDENCE_THRESHOLD:
            v['_suppressed'] = True
            v['human_review_status'] = 'manual_verification_required'
        processed.append(v)

    return processed, primary_finding
