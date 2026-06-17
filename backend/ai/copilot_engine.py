from database.db import (
    get_statistics, get_violations_by_type, get_violations_by_day,
    get_top_repeat_offenders, get_all_violations, get_repeat_offenders,
    get_hotspots, get_violations_by_hour, get_violations_by_location,
)
from ai.repeat_offender import get_top_offenders
from ai.hotspot_analytics import get_hotspot_analysis
from ai.forecast_engine import get_predictions, get_tomorrow_forecast
from datetime import datetime, timedelta


def answer_query(query: str) -> str:
    q = query.lower().strip()

    if 'repeat offender' in q or 'top offender' in q:
        return _repeat_offenders_answer()
    if 'hotspot' in q or 'zone' in q or 'location' in q.lower():
        return _hotspot_answer(q)
    if 'forecast' in q or 'tomorrow' in q or 'predict' in q:
        return _forecast_answer(q)
    if 'daily report' in q or 'generate report' in q:
        return _generate_report_answer('daily')
    if 'weekly report' in q:
        return _generate_report_answer('weekly')
    if 'highest violation' in q or 'most violation' in q:
        return _highest_violations_answer()
    if 'prioritize' in q or 'enforcement' in q:
        return _prioritize_answer()
    if 'increase' in q or 'why' in q:
        return _trend_answer()
    if 'executive' in q or 'summary' in q or 'overview' in q:
        return _executive_summary()

    stats = get_statistics()
    return (
        f"TRINETRA AI - Traffic Enforcement Intelligence\n\n"
        f"Total violations recorded: {stats.get('total', 0)}\n"
        f"Unique vehicles: {stats.get('unique_vehicles', 0)}\n"
        f"High-risk repeat offenders: {stats.get('high_risk_offenders', 0)}\n\n"
        f"Try asking:\n"
        f"- 'Show repeat offenders'\n"
        f"- 'Which location has highest violations?'\n"
        f"- 'What should enforcement teams prioritize?'\n"
        f"- 'Generate daily report'\n"
        f"- 'Violation forecast for tomorrow'\n"
        f"- 'Why did violations increase this week?'"
    )


def _executive_summary() -> str:
    stats = get_statistics()
    offenders = get_top_offenders(limit=5)
    analysis = get_hotspot_analysis()
    location_data = analysis.get('by_location', [])
    type_counts = get_violations_by_type()

    lines = ["**TRINETRA AI — Executive Summary**\n"]
    lines.append(f"*Total violations:* {stats.get('total', 0)}")
    lines.append(f"*Unique vehicles:* {stats.get('unique_vehicles', 0)}")
    lines.append(f"*High-risk offenders:* {stats.get('high_risk_offenders', 0)}")

    if type_counts:
        top = type_counts[0]
        lines.append(f"\n*Most common violation:* {top['type'].replace('_', ' ').title()} ({top['count']} occurrences)")

    if location_data:
        lines.append(f"\n*Top hotspot:* {location_data[0]['location']} ({location_data[0]['count']} violations)")

    if offenders:
        lines.append(f"\n*Top repeat offender:* {offenders[0]['vehicle_number']} — {offenders[0]['total_violations']} violations (Risk: {offenders[0].get('risk_score', 0)})")

    lines.append("\n*Recommendation:* Deploy patrol units to identified hotspots during peak hours (8-10 AM, 5-7 PM). Prioritize high-risk repeat offenders for intervention.")
    return '\n'.join(lines)


def _repeat_offenders_answer() -> str:
    offenders = get_top_offenders(limit=10)
    if not offenders:
        return "No repeat offenders recorded yet."
    lines = ["**Top Repeat Offenders:**"]
    for o in offenders[:10]:
        lines.append(
            f"- `{o['vehicle_number']}` — {o['total_violations']} violations "
            f"(Helmet: {o.get('helmet_violations', 0)}, Overload: {o.get('overloading_violations', 0)}) "
            f"— Risk Score: {o.get('risk_score', 0)} — **{o.get('risk_status', 'LOW')} RISK**"
        )
    return '\n'.join(lines)


def _hotspot_answer(query: str) -> str:
    analysis = get_hotspot_analysis()
    lines = ["**Violation Hotspot Analysis:**"]

    location_data = analysis.get('by_location', [])
    if location_data:
        lines.append("\n*Top Violation Zones:*")
        for loc in location_data[:5]:
            lines.append(f"- {loc['location']}: {loc['count']} violations")

    helmet_zones = analysis.get('top_helmet_zones', [])
    if helmet_zones:
        lines.append("\n*Top Helmet Violation Zones:*")
        for z in helmet_zones[:3]:
            lines.append(f"- {z['location_name']}: {z.get('total', z.get('count', 0))} violations")

    hotspots = analysis.get('hotspots', [])
    if hotspots:
        lines.append(f"\nActive hotspots: {len(hotspots)}")
        critical = [h for h in hotspots if h.get('risk_level') == 'CRITICAL']
        if critical:
            lines.append(f"Critical: {[h['location_name'] for h in critical[:3]]}")

    return '\n'.join(lines)


def _forecast_answer(query: str) -> str:
    if 'tomorrow' in query:
        forecasts = get_tomorrow_forecast()
        if not forecasts:
            forecasts = get_predictions()[:3]
        lines = ["**Tomorrow's Violation Forecast:**"]
    else:
        forecasts = get_predictions()[:5]
        lines = ["**Violation Forecast (Next 3 Days):**"]

    for f in forecasts:
        lines.append(
            f"- {f.get('forecast_date', 'N/A')}: {f.get('violation_type', '').replace('_', ' ').title()} "
            f"— Predicted: {f.get('predicted_count', 0)} — Peak: {f.get('peak_hours', 'N/A')} "
            f"— Confidence: {f.get('confidence', 0) * 100:.0f}%"
        )

    if forecasts:
        lines.append(f"\n*Recommendation:* {forecasts[0].get('recommendation', 'Increase patrols.')}")

    return '\n'.join(lines)


def _generate_report_answer(report_type: str) -> str:
    from ai.report_generator import generate_report
    try:
        result = generate_report(report_type)
        return f"**{report_type.title()} Report Generated**\n- Title: {result['title']}\n- File: {result['file_path']}\n- Download available in Reports section."
    except Exception as e:
        return f"Could not generate report: {str(e)}"


def _highest_violations_answer() -> str:
    analysis = get_hotspot_analysis()
    location_data = analysis.get('by_location', [])
    if location_data:
        top = location_data[0]
        return (
            f"**Highest Violation Location:** `{top['location']}` with {top['count']} violations.\n"
            f"Types: {top.get('types', 'Multiple types')}\n\n"
            f"**Recommendation:** Deploy enforcement team at {top['location']} during peak hours."
        )

    types = get_violations_by_type()
    if types:
        top_type = types[0]
        return f"**Most Common Violation:** {top_type['type'].replace('_', ' ').title()} — {top_type['count']} occurrences."

    return "No violation data available."


def _prioritize_answer() -> str:
    stats = get_statistics()
    offenders = get_top_offenders(limit=5)
    analysis = get_hotspot_analysis()
    location_data = analysis.get('by_location', [])

    lines = ["**Enforcement Prioritization:**\n"]

    if stats.get('high_risk_offenders', 0) > 0:
        lines.append(f"1. **High-Risk Offenders:** {stats['high_risk_offenders']} vehicles flagged — prioritize repeat offender intervention.")

    if location_data:
        top_loc = location_data[0]
        lines.append(f"2. **Hotspot Enforcement:** Focus on `{top_loc['location']}` ({top_loc['count']} violations).")

    type_counts = get_violations_by_type()
    if type_counts:
        top_type = type_counts[0]['type']
        lines.append(f"3. **Primary Violation:** {top_type.replace('_', ' ').title()} — target with dedicated enforcement drives.")

    lines.append("4. **Peak Hours:** Deploy maximum force during 8-10 AM and 5-7 PM.")

    return '\n'.join(lines)


def _trend_answer() -> str:
    today = datetime.now().date()
    this_week_start = today - timedelta(days=today.weekday())
    last_week_start = this_week_start - timedelta(days=7)

    this_week = get_all_violations(date_from=this_week_start.isoformat(), date_to=(today + timedelta(days=1)).isoformat())
    last_week = get_all_violations(date_from=last_week_start.isoformat(), date_to=this_week_start.isoformat())

    this_count = len(this_week)
    last_count = len(last_week)

    if last_count == 0:
        return f"This week: {this_count} violations (baseline not available)."

    diff = this_count - last_count
    pct = (diff / last_count) * 100

    lines = [f"**Violation Trend Analysis:**"]
    lines.append(f"- Last week: {last_count} violations")
    lines.append(f"- This week: {this_count} violations")
    lines.append(f"- Change: {'+' if diff > 0 else ''}{diff} ({pct:+.1f}%)")

    if diff > 0:
        lines.append(f"\n*Likely causes:* Increased traffic volume, seasonal factors, or reduced enforcement presence.")
        lines.append(f"*Recommendation:* Increase patrols during peak hours. Focus on identified hotspots.")
    elif diff < 0:
        lines.append(f"\n*Positive trend:* Enforcement efforts are showing results.")
        lines.append(f"*Recommendation:* Maintain current deployment strategy.")
    else:
        lines.append(f"\n*Stable trend:* Consistent violation patterns.")
        lines.append(f"*Recommendation:* Continue current enforcement levels.")

    return '\n'.join(lines)
