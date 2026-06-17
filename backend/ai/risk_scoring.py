import config
from datetime import datetime


def compute_repeat_offender_risk(total_violations, helmet_count, overloading_count):
    base = 0
    base += helmet_count * config.RISK_SCORES['NO_HELMET']
    base += overloading_count * config.RISK_SCORES['TRIPLE_RIDING']

    priors = max(0, total_violations - 1)
    multiplier_key = min(priors, 4)
    multiplier = config.REPEAT_OFFENDER_MULTIPLIERS.get(multiplier_key, 3.0)

    risk_score = round(base * multiplier, 1)
    risk_status = 'LOW'
    for status, threshold in sorted(config.RISK_STATUS_THRESHOLDS.items(), key=lambda x: -x[1]):
        if risk_score >= threshold:
            risk_status = status
            break
    return risk_score, risk_status


def get_location_multiplier(location_name):
    location_lower = location_name.lower() if location_name else ''
    for key, mult in config.LOCATION_RISK_MULTIPLIERS.items():
        if key in location_lower:
            return mult
    return config.LOCATION_RISK_MULTIPLIERS['default']


def get_time_multiplier(hour=None):
    if hour is None:
        hour = datetime.now().hour
    for period, (start, end, mult) in config.TIME_RISK_MULTIPLIERS.items():
        if period == 'default':
            continue
        if period == 'night':
            if hour >= start or hour < end:
                return mult
        elif start <= hour < end:
            return mult
    return config.TIME_RISK_MULTIPLIERS['default'][2]


def compute_enhanced_risk(violation_type, location='', hour=None):
    base = config.RISK_SCORES.get(violation_type, 30)
    loc_mult = get_location_multiplier(location)
    time_mult = get_time_multiplier(hour)
    return round(base * loc_mult * time_mult, 1)


def get_risk_status(score):
    for status, threshold in sorted(config.RISK_STATUS_THRESHOLDS.items(), key=lambda x: -x[1]):
        if score >= threshold:
            return status
    return 'LOW'
