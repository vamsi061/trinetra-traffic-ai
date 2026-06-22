"""Violation Prioritization & False Positive Suppression for TRINETRA AI v3.

Pipeline:
  1. validate_violation_context — reject violations missing required scene evidence
  2. environment_confidence_modifier — adjust confidence based on image quality
  3. calculate_evidence_score — rate each violation's evidential support
  4. apply_threshold — violation-specific thresholds + Florence context boost
  5. rank_violations — by scene relevance + confidence + context score
  6. select_primary — highest-ranked violation becomes the Primary Finding
  7. suppress_secondary — hide low-scoring secondary violations behind review flag
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================
# FIX 5: Violation-specific confidence thresholds
# ============================================================
VIOLATION_THRESHOLDS = {
    'NO_HELMET':                   {'floor': 0.50, 'possible_ceiling': 0.70},
    'HELMET_ASSESSMENT_UNCERTAIN': {'floor': 0.35, 'possible_ceiling': 0.55},
    'SEATBELT_VIOLATION':          {'floor': 0.70, 'possible_ceiling': 0.80},
    'TRIPLE_RIDING':               {'floor': 0.50, 'possible_ceiling': 0.70},
    'MOTORCYCLE_OVERLOADING':      {'floor': 0.50, 'possible_ceiling': 0.70},
    'MOTORCYCLE_EXTREME_OVERLOADING': {'floor': 0.50, 'possible_ceiling': 0.70},
    'POSSIBLE_ILLEGAL_PARKING':    {'floor': 0.65, 'possible_ceiling': 0.80},
    'WRONG_SIDE_DRIVING':          {'floor': 0.80, 'possible_ceiling': 0.90},
    'STOP_LINE_VIOLATION':         {'floor': 0.55, 'possible_ceiling': 0.75},
    'RED_LIGHT_VIOLATION':         {'floor': 0.60, 'possible_ceiling': 0.80},
}

DEFAULT_THRESHOLDS = {'floor': 0.50, 'possible_ceiling': 0.70}

# Evidence score floor (applied uniformly)
EVIDENCE_FLOOR = 0.30
# Secondary suppression threshold
EVIDENCE_THRESHOLD = 0.50

# ============================================================
# FIX 4: Environment-aware confidence modifiers
# ============================================================
ENVIRONMENT_MODIFIERS = {
    'Low Light':   0.85,
    'Fog/Haze':    0.85,
    'Glare':       0.85,
    'Blur':        0.80,
    'Low Contrast': 0.90,
    'Shadow':      0.85,
    'Rain':        0.85,
}

# Compound discount: when multiple issues stack, apply diminishing returns
ENVIRONMENT_STACKING = {
    1: 1.0,     # single issue: use modifier directly
    2: 0.85,    # two issues: 85% of the weaker modifier
    3: 0.70,    # three issues: 70%
    4: 0.55,    # four issues: 55%
}


def environment_confidence_modifier(confidence, quality_analysis):
    """Adjust confidence based on image quality issues.

    Args:
        confidence: raw violation confidence
        quality_analysis: dict from analyze_image_quality() or assess_quality()

    Returns:
        (adjusted_confidence: float, issues_found: list[str])
    """
    if not quality_analysis:
        return confidence, []

    issues = []
    if isinstance(quality_analysis, dict):
        issues = quality_analysis.get('issues', [])

    if not issues:
        return confidence, []

    matched = []
    for issue in issues:
        modifier = ENVIRONMENT_MODIFIERS.get(issue)
        if modifier is not None:
            matched.append((issue, modifier))

    if not matched:
        return confidence, []

    # Use the weakest modifier
    weakest = min(m for _, m in matched)
    n_issues = len(matched)

    stacking = ENVIRONMENT_STACKING.get(n_issues, 0.40)
    env_factor = weakest * stacking

    adjusted = confidence * env_factor
    adjusted = max(0.10, min(1.0, adjusted))

    return adjusted, [issue for issue, _ in matched]


# ============================================================
# FIX 6: Florence context boost
# ============================================================
SCENE_KEYWORDS = {
    'POSSIBLE_ILLEGAL_PARKING': ['parked', 'parking', 'stationary', 'stopped',
                                  'curb', 'kerb', 'footpath', 'roadside',
                                  'no parking', 'parking zone', 'restricted'],
    'NO_HELMET': ['helmet', 'rider', 'motorcycle', 'scooter', 'without helmet',
                  'no helmet'],
    'HELMET_ASSESSMENT_UNCERTAIN': ['helmet', 'rider', 'motorcycle'],
    'SEATBELT_VIOLATION': ['seatbelt', 'seat belt', 'car', 'driver', 'occupant',
                           'cabin', 'windscreen'],
    'TRIPLE_RIDING': ['triple', 'three', 'three people', 'three persons',
                      'overloaded', 'overloading'],
    'STOP_LINE_VIOLATION': ['stop line', 'stop', 'halt', 'crossed', 'intersection'],
    'WRONG_SIDE_DRIVING': ['wrong side', 'wrong-way', 'oncoming', 'opposite'],
    'RED_LIGHT_VIOLATION': ['red light', 'signal', 'traffic light'],
}

# Context prerequisites
CONTEXT_REQUIREMENTS = {
    'POSSIBLE_ILLEGAL_PARKING': {'any_of': ['car', 'motorcycle', 'truck', 'bus', 'person']},
    'NO_HELMET': {'all_of': ['motorcycle', 'person']},
    'HELMET_ASSESSMENT_UNCERTAIN': {'all_of': ['motorcycle', 'person']},
    'SEATBELT_VIOLATION': {'all_of': ['car', 'person']},
    'TRIPLE_RIDING': {'all_of': ['motorcycle', 'person']},
    'STOP_LINE_VIOLATION': {},
    'WRONG_SIDE_DRIVING': {'all_of': ['car', 'motorcycle', 'truck', 'bus']},
    'RED_LIGHT_VIOLATION': {'any_of': ['traffic light', 'car', 'motorcycle']},
    'STOP_LINE_VIOLATION': {'any_of': ['car', 'motorcycle', 'truck', 'bus']},
    'MOTORCYCLE_OVERLOADING': {'all_of': ['motorcycle', 'person']},
    'MOTORCYCLE_EXTREME_OVERLOADING': {'all_of': ['motorcycle', 'person']},
}

# Evidence factor weights
EVIDENCE_WEIGHTS = {
    'POSSIBLE_ILLEGAL_PARKING': {
        'has_parking_context': 0.40, 'vehicle_large_enough': 0.25,
        'scene_mentions_parking': 0.20, 'not_moving': 0.15,
    },
    'NO_HELMET': {
        'has_motorcycle': 0.30, 'has_person': 0.30,
        'model_available': 0.25, 'scene_mentions_rider': 0.15,
    },
    'HELMET_ASSESSMENT_UNCERTAIN': {
        'has_motorcycle': 0.25, 'has_person': 0.25,
        'hsv_suggested_absent': 0.30, 'scene_mentions_rider': 0.20,
    },
    'SEATBELT_VIOLATION': {
        'has_car': 0.35, 'person_in_car': 0.35,
        'cabin_visible': 0.20, 'scene_mentions_car': 0.10,
    },
    'TRIPLE_RIDING': {
        'has_motorcycle': 0.30, 'rider_count_ge_3': 0.40,
        'scene_mentions_overload': 0.15, 'association_confidence': 0.15,
    },
    'MOTORCYCLE_OVERLOADING': {
        'has_motorcycle': 0.25, 'rider_count_ge_4': 0.45,
        'scene_mentions_overload': 0.15, 'association_confidence': 0.15,
    },
    'MOTORCYCLE_EXTREME_OVERLOADING': {
        'has_motorcycle': 0.20, 'rider_count_ge_5': 0.50,
        'scene_mentions_overload': 0.15, 'association_confidence': 0.15,
    },
    'STOP_LINE_VIOLATION': {
        'stop_line_detected': 0.30, 'vehicle_past_line': 0.30,
        'line_visible': 0.15, 'scene_mentions_stop': 0.25,
    },
    'RED_LIGHT_VIOLATION': {
        'traffic_light_detected': 0.25, 'signal_red': 0.30,
        'vehicle_past_line': 0.25, 'scene_mentions_red_light': 0.20,
    },
    'WRONG_SIDE_DRIVING': {
        'lane_evidence': 0.35, 'motion_validated': 0.35,
        'scene_mentions_wrong_side': 0.30,
    },
}


def _scene_relevance_boost(violation_type, narrative):
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
        factors['vehicle_large_enough'] = 0.8
        factors['scene_mentions_parking'] = 0.5 if _scene_relevance_boost(vtype, scene_info.get('narrative')) > 0 else 0.0
        factors['not_moving'] = 1.0

    elif vtype == 'SEATBELT_VIOLATION':
        factors['has_car'] = 1.0 if 'car' in labels else 0.0
        factors['person_in_car'] = 1.0 if violation.get('person_bbox') and violation.get('vehicle_bbox') else 0.0
        factors['cabin_visible'] = 0.5
        factors['scene_mentions_car'] = 0.5 if _scene_relevance_boost(vtype, scene_info.get('narrative')) > 0 else 0.0

    elif vtype == 'NO_HELMET':
        factors['has_motorcycle'] = 1.0 if 'motorcycle' in labels else 0.0
        factors['has_person'] = 1.0 if 'person' in labels else 0.0
        model_avail = violation.get('helmet_state') != 'HELMET_UNKNOWN'
        factors['model_available'] = 1.0 if model_avail else 0.0
        factors['scene_mentions_rider'] = 0.5 if _scene_relevance_boost(vtype, scene_info.get('narrative')) > 0 else 0.0

    elif vtype == 'HELMET_ASSESSMENT_UNCERTAIN':
        factors['has_motorcycle'] = 1.0 if 'motorcycle' in labels else 0.0
        factors['has_person'] = 1.0 if 'person' in labels else 0.0
        factors['hsv_suggested_absent'] = 0.7
        factors['scene_mentions_rider'] = 0.5 if _scene_relevance_boost(vtype, scene_info.get('narrative')) > 0 else 0.0

    elif vtype == 'TRIPLE_RIDING':
        rider_count = violation.get('rider_count', 0)
        factors['has_motorcycle'] = 1.0 if 'motorcycle' in labels else 0.0
        factors['rider_count_ge_3'] = 1.0 if rider_count >= 3 else 0.0
        factors['scene_mentions_overload'] = 0.5 if _scene_relevance_boost(vtype, scene_info.get('narrative')) > 0 else 0.0
        factors['association_confidence'] = min(1.0, violation.get('confidence', 0))

    elif vtype == 'MOTORCYCLE_OVERLOADING':
        rider_count = violation.get('rider_count', 0)
        factors['has_motorcycle'] = 1.0 if 'motorcycle' in labels else 0.0
        factors['rider_count_ge_4'] = 1.0 if rider_count >= 4 else 0.0
        factors['scene_mentions_overload'] = 0.5 if _scene_relevance_boost(vtype, scene_info.get('narrative')) > 0 else 0.0
        factors['association_confidence'] = min(1.0, violation.get('confidence', 0))

    elif vtype == 'MOTORCYCLE_EXTREME_OVERLOADING':
        rider_count = violation.get('rider_count', 0)
        factors['has_motorcycle'] = 1.0 if 'motorcycle' in labels else 0.0
        factors['rider_count_ge_5'] = 1.0 if rider_count >= 5 else 0.0
        factors['scene_mentions_overload'] = 0.5 if _scene_relevance_boost(vtype, scene_info.get('narrative')) > 0 else 0.0
        factors['association_confidence'] = min(1.0, violation.get('confidence', 0))

    elif vtype == 'STOP_LINE_VIOLATION':
        factors['stop_line_detected'] = 1.0 if violation.get('stop_line_y') else 0.0
        factors['vehicle_past_line'] = 0.7
        diag = violation.get('stop_line_diagnostics', {})
        factors['line_visible'] = diag.get('line_visibility_score', 0.5)
        factors['scene_mentions_stop'] = 0.5 if _scene_relevance_boost(vtype, scene_info.get('narrative')) > 0 else 0.0

    elif vtype == 'RED_LIGHT_VIOLATION':
        factors['traffic_light_detected'] = 1.0 if violation.get('traffic_light_bbox') else 0.0
        diag = violation.get('red_light_diagnostics', {})
        factors['signal_red'] = (diag.get('signal_visibility', 0.0) + diag.get('signal_brightness', 0.0)) / 2.0
        factors['vehicle_past_line'] = diag.get('vehicle_position_score', 0.5)
        factors['scene_mentions_red_light'] = 0.5 if _scene_relevance_boost(vtype, scene_info.get('narrative')) > 0 else 0.0

    elif vtype == 'WRONG_SIDE_DRIVING':
        factors['lane_evidence'] = 0.8
        motion = violation.get('_motion_validated', {})
        factors['motion_validated'] = 1.0 if motion.get('is_moving') else 0.0
        factors['scene_mentions_wrong_side'] = 0.5 if _scene_relevance_boost(vtype, scene_info.get('narrative')) > 0 else 0.0

    else:
        factors['default'] = 0.5

    for key, weight in weights.items():
        val = factors.get(key, 0.5)
        score += val * weight

    return min(1.0, score), factors


def validate_violation_context(violation, detections):
    vtype = violation['violation_type']
    reqs = CONTEXT_REQUIREMENTS.get(vtype)
    if not reqs:
        return True, ''

    labels = [d['label'] for d in detections]

    for label in reqs.get('all_of', []):
        if label not in labels:
            return False, f'Required detection "{label}" not present in scene'

    for label in reqs.get('any_of', []):
        if any(l in labels for l in ([label] if isinstance(label, str) else label)):
            break
    else:
        if reqs.get('any_of'):
            return False, f'None of required detections {reqs["any_of"]} present in scene'

    return True, ''


def apply_threshold(violation, quality_analysis=None):
    """Apply violation-type-specific confidence and evidence thresholds.

    Args:
        violation: violation dict
        quality_analysis: optional quality analysis dict for env adjustment

    Returns:
        (action: str, display_type: str, needs_review: bool)
    """
    raw_conf = violation.get('confidence', 0)
    evidence = violation.get('_evidence_score', 1.0)
    vtype = violation['violation_type']

    # FIX 4: Environment-aware confidence adjustment.
    # Skip for occupancy violations (triple_riding/overloading) — they rely on
    # rider counting, not visual detail, so image quality is irrelevant.
    if quality_analysis and vtype not in ('TRIPLE_RIDING', 'MOTORCYCLE_OVERLOADING',
                                           'MOTORCYCLE_EXTREME_OVERLOADING'):
        adjusted_conf, env_issues = environment_confidence_modifier(raw_conf, quality_analysis)
        violation['_environment_issues'] = env_issues
        if adjusted_conf < raw_conf:
            violation['_environment_adjusted'] = True
            violation['_environment_modifier'] = round(adjusted_conf / raw_conf, 3) if raw_conf > 0 else 1.0
            raw_conf = adjusted_conf

    thresholds = VIOLATION_THRESHOLDS.get(vtype, DEFAULT_THRESHOLDS)
    floor = thresholds['floor']
    ceiling = thresholds['possible_ceiling']

    if raw_conf < floor:
        return 'discard', '', False

    if evidence < EVIDENCE_FLOOR:
        return 'discard', '', False

    # FIX 6: Florence scene relevance boost can elevate "possible" → "confirmed"
    narrative = violation.get('_scene_narrative', '')
    scene_boost = _scene_relevance_boost(vtype, narrative)

    display = violation.get('display_type', vtype.replace('_', ' ').title())

    if raw_conf < ceiling:
        # Scene relevance can confirm borderline cases
        if scene_boost > 0.15 and raw_conf >= floor * 1.2:
            return 'confirmed', display, evidence < 0.60
        pfx = 'Possible '
        display = f'{pfx}{display}' if not display.startswith(pfx) else display
        return 'possible', display, True

    needs_review = evidence < 0.60
    return 'confirmed', display, needs_review


def _occupancy_boost(violation):
    """Boost priority for occupancy violations with confirmed rider counts.
    
    Only applies to TRIPLE_RIDING and MOTORCYCLE_OVERLOADING (not EXTREME) —
    EXTREME_OVERLOADING at conf~0.80 naturally outranks NO_HELMET without boost,
    and boosting it causes wrong primaries in PARKING/HELMET_MISSING images.
    """
    vtype = violation['violation_type']
    rider_count = violation.get('rider_count', 0)
    if vtype == 'TRIPLE_RIDING' and rider_count >= 3:
        return 0.15
    if vtype == 'MOTORCYCLE_OVERLOADING' and rider_count >= 4:
        return 0.15
    return 0.0


def rank_violations(violations, scene_info, detections):
    ranked = []
    narrative = scene_info.get('narrative', '') if scene_info else ''

    for v in violations:
        raw_conf = v.get('confidence', 0)
        evidence_score, factors = _evidence_factors(v, detections, scene_info)
        v['_evidence_score'] = evidence_score
        v['_evidence_factors'] = factors
        v['_scene_narrative'] = narrative
        scene_boost = _scene_relevance_boost(v['violation_type'], narrative)
        occ_boost = _occupancy_boost(v)

        combined = (raw_conf * 0.40) + (evidence_score * 0.35) + (scene_boost * 0.25) + occ_boost
        v['_priority_score'] = round(combined, 3)
        ranked.append((combined, v))

    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked


def select_primary(violations, scene_info, detections, quality_analysis=None):
    """Main pipeline with v3 upgrades: env-aware, violation-specific, Florence boost."""
    if not violations:
        return [], None

    # Step 1: Context validation
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

    # Step 3: Apply thresholds (env-aware, violation-specific)
    passed = []
    for v in valid_violations:
        action, display, needs_review = apply_threshold(v, quality_analysis)
        if action == 'discard':
            logger.debug(
                f'Discarded {v.get("violation_type")} '
                f'(conf={v.get("confidence"):.2f}, evidence={v.get("_evidence_score", 0):.2f})'
            )
            continue
        v['display_type'] = display
        v['needs_review'] = needs_review or v.get('needs_review', False)
        if action == 'possible':
            v['human_review_status'] = 'manual_verification_required'
        passed.append(v)

    if not passed:
        return [], None

    # Step 4: Rank
    ranked = rank_violations(passed, scene_info, detections)

    # Step 5: Select primary
    top_score, primary = ranked[0]
    primary['_is_primary'] = True
    vtype = primary['violation_type']
    narrative = scene_info.get('narrative', '') if scene_info else ''
    scene_boost = _scene_relevance_boost(vtype, narrative)

    reason_parts = []
    env_issues = primary.get('_environment_issues', [])
    if env_issues:
        reason_parts.append(f'Environment adjusted: {", ".join(env_issues)}')
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
    if primary.get('_environment_adjusted'):
        primary_finding['environment_modifier'] = primary.get('_environment_modifier', 1.0)
        primary_finding['environment_issues'] = env_issues

    # Step 6: Suppress low-evidence secondaries
    processed = []
    for _, v in ranked:
        if v.get('_is_primary'):
            processed.append(v)
            continue
        if v.get('_evidence_score', 0) < EVIDENCE_THRESHOLD:
            v['_suppressed'] = True
            v['human_review_status'] = 'manual_verification_required'
        processed.append(v)

    return processed, primary_finding
