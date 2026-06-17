from datetime import datetime, timedelta
from database.db import get_all_violations, save_forecast, get_forecasts, get_violations_by_type, get_violations_by_day
import config


def generate_forecast():
    today = datetime.now().date()
    lookback = today - timedelta(days=config.FORECAST_LOOKBACK_DAYS)

    past_violations = get_all_violations(
        date_from=lookback.isoformat(),
        date_to=today.isoformat(),
    )

    type_counts = {}
    for v in past_violations:
        vt = v.violation_type
        type_counts[vt] = type_counts.get(vt, 0) + 1

    if not type_counts:
        return _default_forecast(today)

    total_past = len(past_violations)
    daily_avg = total_past / max(config.FORECAST_LOOKBACK_DAYS, 1)

    forecasts = []
    for day_offset in range(1, 4):
        forecast_date = today + timedelta(days=day_offset)
        for violation_type, count in type_counts.items():
            proportion = count / total_past
            predicted = max(1, round(daily_avg * proportion * config.FORECAST_CONFIDENCE_DECAY ** day_offset))
            confidence = round(max(0.3, 1.0 - (day_offset * 0.15)), 2)

            peak_hours = _predict_peak_hours(violation_type)
            recommendation = _generate_recommendation(violation_type, predicted, peak_hours)

            save_forecast(
                forecast_date=forecast_date.isoformat(),
                violation_type=violation_type,
                predicted_count=predicted,
                confidence=confidence,
                peak_hours=peak_hours,
                recommendation=recommendation,
            )
            forecasts.append({
                'forecast_date': forecast_date.isoformat(),
                'violation_type': violation_type,
                'predicted_count': predicted,
                'confidence': confidence,
                'peak_hours': peak_hours,
                'recommendation': recommendation,
            })

    return forecasts


def get_predictions():
    stored = get_forecasts(limit=10)
    if stored:
        return stored
    return generate_forecast()


def get_tomorrow_forecast():
    tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
    all_f = get_forecasts(limit=20)
    return [f for f in all_f if f.get('forecast_date', '') == tomorrow]


def _predict_peak_hours(violation_type):
    peak_map = {
        'NO_HELMET': '8AM - 10AM, 5PM - 7PM',
        'TRIPLE_RIDING': '8AM - 9AM, 6PM - 7PM',
        'MOTORCYCLE_OVERLOADING': '9AM - 11AM',
        'MOTORCYCLE_EXTREME_OVERLOADING': '9AM - 11AM',
        'WRONG_SIDE_DRIVING': '10AM - 12PM, 4PM - 6PM',
    }
    return peak_map.get(violation_type, '8AM - 10AM, 5PM - 7PM')


def _generate_recommendation(violation_type, predicted, peak_hours):
    recs = {
        'NO_HELMET': f'Deploy 2 traffic officers at high-traffic intersections during {peak_hours}. Conduct helmet awareness drive.',
        'TRIPLE_RIDING': f'Set up checkpoints near schools and metro stations during {peak_hours}.',
        'MOTORCYCLE_OVERLOADING': f'Deploy enforcement team near bus stands and market areas during {peak_hours}.',
        'WRONG_SIDE_DRIVING': f'Install barriers at known wrong-side entry points. Deploy officers during {peak_hours}.',
    }
    return recs.get(violation_type, f'Increase patrols during {peak_hours}. Expected {predicted} violations.')


def _default_forecast(today):
    return [{
        'forecast_date': (today + timedelta(days=i)).isoformat(),
        'violation_type': 'NO_HELMET',
        'predicted_count': 5,
        'confidence': 0.5,
        'peak_hours': '8AM - 10AM',
        'recommendation': 'Deploy 2 traffic officers at major intersections.',
    } for i in range(1, 4)]
