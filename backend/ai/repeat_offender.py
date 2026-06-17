from database.db import upsert_repeat_offender, get_repeat_offenders
from ai.risk_scoring import compute_repeat_offender_risk, get_risk_status


def register_violation(vehicle_number, violation_type, timestamp):
    if not vehicle_number:
        return
    upsert_repeat_offender(vehicle_number, violation_type, timestamp)


def get_top_offenders(limit=20, risk_status=None):
    offenders = get_repeat_offenders(limit=limit, risk_status=risk_status)
    for o in offenders:
        o['display_status'] = _get_status_badge(o['risk_status'])
    return offenders


def search_offender(vehicle_number):
    offenders = get_repeat_offenders(limit=100)
    return [o for o in offenders if vehicle_number.upper() in o['vehicle_number'].upper()]


def _get_status_badge(status):
    badges = {
        'CRITICAL': 'bg-red-500/20 text-red-300',
        'HIGH': 'bg-orange-500/20 text-orange-300',
        'MEDIUM': 'bg-yellow-500/20 text-yellow-300',
        'LOW': 'bg-green-500/20 text-green-300',
    }
    return badges.get(status, 'bg-gray-500/20 text-gray-300')
