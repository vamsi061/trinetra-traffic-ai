from database.db import get_hotspots, get_top_hotspot_zones, upsert_hotspot, get_violations_by_location, get_violations_by_hour
from ai.risk_scoring import compute_enhanced_risk, get_risk_status


HOTSPOT_LOCATIONS = [
    'Majestic Bus Stand', 'KR Market', 'Silk Board Junction',
    'Marathahalli Bridge', 'Hebbal Flyover', 'MG Road',
    'Brigade Road', 'Commercial Street', 'Jayanagar 4th Block',
    'Indiranagar 100ft Road', 'Koramangala Sony World',
    'Yeshwanthpur Station', 'Nayandahalli Junction', 'Peenya Industrial Area',
]


def register_hotspot_violation(violation_type, location=None):
    loc = location or _simulate_location()
    upsert_hotspot(loc, violation_type)


def get_hotspot_analysis():
    hotspots = get_hotspots(min_count=1)
    top_helmet_zones = get_top_hotspot_zones(limit=10, violation_type='NO_HELMET')
    top_overloading_zones = get_top_hotspot_zones(limit=10, violation_type='TRIPLE_RIDING')
    top_high_risk = get_top_hotspot_zones(limit=10)

    location_data = get_violations_by_location()
    hourly_data = get_violations_by_hour()

    return {
        'hotspots': hotspots,
        'top_helmet_zones': top_helmet_zones,
        'top_overloading_zones': top_overloading_zones,
        'top_high_risk_areas': top_high_risk,
        'by_location': location_data,
        'by_hour': hourly_data,
    }


def _simulate_location():
    import random
    return random.choice(HOTSPOT_LOCATIONS)
