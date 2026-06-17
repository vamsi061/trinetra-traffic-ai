"""Vehicle Risk Profile Engine — computes risk profiles and watchlist status."""
import config


def compute_vehicle_risk_profile(vehicle_number, violations, offender_data=None):
    """Build a risk profile card for a vehicle.

    Args:
        vehicle_number: plate number
        violations: list of ViolationRecord objects
        offender_data: optional dict from repeat_offender module

    Returns:
        dict with risk profile
    """
    total = len(violations) if violations else 0
    helmet_count = sum(1 for v in (violations or []) if v.violation_type == 'NO_HELMET')
    overloading_count = sum(1 for v in (violations or []) if v.violation_type in ('TRIPLE_RIDING', 'MOTORCYCLE_OVERLOADING', 'MOTORCYCLE_EXTREME_OVERLOADING'))

    risk_score = 0
    risk_score += helmet_count * config.RISK_SCORES.get('NO_HELMET', 30)
    risk_score += overloading_count * max(config.RISK_SCORES.get('TRIPLE_RIDING', 75), config.RISK_SCORES.get('MOTORCYCLE_OVERLOADING', 95))
    priors = max(0, total - 1)
    mult_key = min(priors, 4)
    multiplier = config.REPEAT_OFFENDER_MULTIPLIERS.get(mult_key, 3.0)
    risk_score = min(round(risk_score * multiplier, 1), 100)

    if risk_score >= 75:
        risk_level = 'CRITICAL'
    elif risk_score >= 50:
        risk_level = 'HIGH'
    elif risk_score >= 25:
        risk_level = 'MEDIUM'
    else:
        risk_level = 'LOW'

    # Watchlist eligibility
    watchlist = total >= 5 or helmet_count >= 3 or overloading_count >= 2 or risk_level in ('HIGH', 'CRITICAL')

    last_seen = max((v.timestamp for v in (violations or []) if v.timestamp), default=None)

    return {
        'vehicle_number': vehicle_number,
        'total_violations': total,
        'helmet_violations': helmet_count,
        'overloading_violations': overloading_count,
        'risk_score': risk_score,
        'risk_level': risk_level,
        'watchlist': watchlist,
        'officer_attention': 'Recommended' if watchlist else 'Standard monitoring',
        'last_seen': last_seen.isoformat() if last_seen else None,
    }
