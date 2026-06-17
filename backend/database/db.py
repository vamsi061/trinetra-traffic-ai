import sqlite3
from datetime import datetime, timedelta
from .models import ViolationRecord
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_number TEXT DEFAULT '',
            vehicle_type TEXT DEFAULT '',
            violation_type TEXT NOT NULL,
            confidence REAL DEFAULT 0.0,
            image_path TEXT DEFAULT '',
            evidence_path TEXT DEFAULT '',
            location TEXT DEFAULT '',
            timestamp TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_violation_type
        ON violations(violation_type)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp
        ON violations(timestamp)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vehicle_number
        ON violations(vehicle_number)
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repeat_offenders (
            vehicle_number TEXT PRIMARY KEY,
            total_violations INTEGER DEFAULT 0,
            helmet_violations INTEGER DEFAULT 0,
            overloading_violations INTEGER DEFAULT 0,
            seatbelt_violations INTEGER DEFAULT 0,
            wrong_side_violations INTEGER DEFAULT 0,
            risk_score REAL DEFAULT 0.0,
            risk_status TEXT DEFAULT 'LOW',
            last_violation_date TEXT,
            first_seen_date TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS violation_hotspots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_name TEXT DEFAULT '',
            latitude REAL DEFAULT 0.0,
            longitude REAL DEFAULT 0.0,
            violation_type TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            risk_level TEXT DEFAULT 'LOW',
            last_updated TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            forecast_date TEXT NOT NULL,
            violation_type TEXT NOT NULL,
            predicted_count INTEGER DEFAULT 0,
            confidence REAL DEFAULT 0.0,
            peak_hours TEXT DEFAULT '',
            recommendation TEXT DEFAULT '',
            generated_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type TEXT NOT NULL,
            title TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            generated_at TEXT,
            file_path TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()


def insert_violation(record):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO violations
            (vehicle_number, vehicle_type, violation_type,
             confidence, image_path, evidence_path, location, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record.vehicle_number,
        record.vehicle_type,
        record.violation_type,
        record.confidence,
        record.image_path,
        record.evidence_path,
        record.location if hasattr(record, 'location') else '',
        record.timestamp,
    ))
    conn.commit()
    conn.close()


def get_all_violations(vehicle_number=None, violation_type=None, date_from=None, date_to=None, location=None):
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM violations WHERE 1=1"
    params = []
    if vehicle_number:
        query += " AND vehicle_number LIKE ?"
        params.append(f'%{vehicle_number}%')
    if violation_type:
        query += " AND violation_type = ?"
        params.append(violation_type)
    if date_from:
        query += " AND timestamp >= ?"
        params.append(date_from)
    if date_to:
        query += " AND timestamp <= ?"
        params.append(date_to)
    if location:
        query += " AND location LIKE ?"
        params.append(f'%{location}%')
    query += " ORDER BY timestamp DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [ViolationRecord.from_row(row) for row in rows]


def get_statistics():
    conn = get_connection()
    cursor = conn.cursor()
    stats = {}
    cursor.execute("SELECT COUNT(*) FROM violations")
    stats['total'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM violations WHERE violation_type='NO_HELMET'")
    stats['no_helmet'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM violations WHERE violation_type='TRIPLE_RIDING'")
    stats['triple_riding'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM violations WHERE violation_type='MOTORCYCLE_OVERLOADING'")
    stats['motorcycle_overloading'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM violations WHERE violation_type='MOTORCYCLE_EXTREME_OVERLOADING'")
    stats['motorcycle_extreme_overloading'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM violations WHERE violation_type='WRONG_SIDE_DRIVING'")
    stats['wrong_side'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT vehicle_number) FROM violations WHERE vehicle_number != ''")
    stats['unique_vehicles'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM repeat_offenders WHERE risk_status='HIGH' OR risk_status='CRITICAL'")
    stats['high_risk_offenders'] = cursor.fetchone()[0]
    conn.close()
    return stats


def get_violations_by_type():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT violation_type, COUNT(*) as count
        FROM violations
        GROUP BY violation_type
        ORDER BY count DESC
    """)
    results = cursor.fetchall()
    conn.close()
    return [{'type': r['violation_type'], 'count': r['count']} for r in results]


def get_violations_by_day(days=30):
    conn = get_connection()
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    cursor.execute("""
        SELECT DATE(timestamp) as day, COUNT(*) as count
        FROM violations
        WHERE timestamp >= ?
        GROUP BY DATE(timestamp)
        ORDER BY day
    """, (cutoff,))
    results = cursor.fetchall()
    conn.close()
    return [{'day': r['day'], 'count': r['count']} for r in results]


def get_violations_by_hour():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour, COUNT(*) as count
        FROM violations
        GROUP BY hour
        ORDER BY hour
    """)
    results = cursor.fetchall()
    conn.close()
    return [{'hour': r['hour'], 'count': r['count']} for r in results]


def get_violations_by_location():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT location, COUNT(*) as count, GROUP_CONCAT(DISTINCT violation_type) as types
        FROM violations
        WHERE location != ''
        GROUP BY location
        ORDER BY count DESC
    """)
    results = cursor.fetchall()
    conn.close()
    return [{'location': r['location'], 'count': r['count'], 'types': r['types']} for r in results]


def get_top_repeat_offenders(limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT vehicle_number, COUNT(*) as violation_count,
               GROUP_CONCAT(DISTINCT violation_type) as violation_types
        FROM violations
        WHERE vehicle_number != ''
        GROUP BY vehicle_number
        ORDER BY violation_count DESC
        LIMIT ?
    """, (limit,))
    results = cursor.fetchall()
    conn.close()
    return [{
        'vehicle': r['vehicle_number'],
        'count': r['violation_count'],
        'types': r['violation_types'],
    } for r in results]


def get_monthly_trend(months=6):
    conn = get_connection()
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=30 * months)).isoformat()
    cursor.execute("""
        SELECT strftime('%Y-%m', timestamp) as month,
               COUNT(*) as count
        FROM violations
        WHERE timestamp >= ?
        GROUP BY strftime('%Y-%m', timestamp)
        ORDER BY month
    """, (cutoff,))
    results = cursor.fetchall()
    conn.close()
    return [{'month': r['month'], 'count': r['count']} for r in results]


def get_recent_violations(limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM violations
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [ViolationRecord.from_row(row) for row in rows]


# —————— Repeat Offender Queries ——————

def upsert_repeat_offender(vehicle_number, violation_type, timestamp):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repeat_offenders WHERE vehicle_number=?", (vehicle_number,))
    existing = cursor.fetchone()
    if existing:
        total = existing['total_violations'] + 1
        helmet = existing['helmet_violations'] + (1 if violation_type == 'NO_HELMET' else 0)
        overloading = existing['overloading_violations'] + (1 if violation_type in ('TRIPLE_RIDING', 'MOTORCYCLE_OVERLOADING', 'MOTORCYCLE_EXTREME_OVERLOADING') else 0)
        seatbelt = existing['seatbelt_violations'] + (1 if violation_type == 'SEATBELT_VIOLATION' else 0)
        wrong_side = existing['wrong_side_violations'] + (1 if violation_type == 'WRONG_SIDE_DRIVING' else 0)
        from ai.risk_scoring import compute_repeat_offender_risk
        risk_score, risk_status = compute_repeat_offender_risk(total, helmet, overloading)
        cursor.execute("""
            UPDATE repeat_offenders SET
                total_violations=?, helmet_violations=?, overloading_violations=?,
                seatbelt_violations=?, wrong_side_violations=?,
                risk_score=?, risk_status=?, last_violation_date=?
            WHERE vehicle_number=?
        """, (total, helmet, overloading, seatbelt, wrong_side, risk_score, risk_status, timestamp, vehicle_number))
    else:
        helmet = 1 if violation_type == 'NO_HELMET' else 0
        overloading = 1 if violation_type in ('TRIPLE_RIDING', 'MOTORCYCLE_OVERLOADING', 'MOTORCYCLE_EXTREME_OVERLOADING') else 0
        seatbelt = 1 if violation_type == 'SEATBELT_VIOLATION' else 0
        wrong_side = 1 if violation_type == 'WRONG_SIDE_DRIVING' else 0
        from ai.risk_scoring import compute_repeat_offender_risk
        risk_score, risk_status = compute_repeat_offender_risk(1, helmet, overloading)
        cursor.execute("""
            INSERT INTO repeat_offenders
                (vehicle_number, total_violations, helmet_violations, overloading_violations,
                 seatbelt_violations, wrong_side_violations, risk_score, risk_status,
                 last_violation_date, first_seen_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (vehicle_number, 1, helmet, overloading, seatbelt, wrong_side, risk_score, risk_status, timestamp, timestamp))
    conn.commit()
    conn.close()


def get_repeat_offenders(limit=20, risk_status=None):
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM repeat_offenders WHERE total_violations > 0"
    params = []
    if risk_status:
        query += " AND risk_status = ?"
        params.append(risk_status)
    query += " ORDER BY risk_score DESC LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# —————— Hotspot Queries ——————

def upsert_hotspot(location_name, violation_type):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM violation_hotspots WHERE location_name=? AND violation_type=?",
        (location_name, violation_type)
    )
    existing = cursor.fetchone()
    now = datetime.now().isoformat()
    if existing:
        cursor.execute(
            "UPDATE violation_hotspots SET count=count+1, last_updated=? WHERE id=?",
            (now, existing['id'])
        )
    else:
        cursor.execute("""
            INSERT INTO violation_hotspots (location_name, violation_type, count, risk_level, last_updated)
            VALUES (?, ?, 1, 'LOW', ?)
        """, (location_name, violation_type, now))
    conn.commit()
    conn.close()


def get_hotspots(min_count=2):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT location_name, violation_type, count,
               CASE
                   WHEN count >= 10 THEN 'CRITICAL'
                   WHEN count >= 5 THEN 'HIGH'
                   WHEN count >= 3 THEN 'MEDIUM'
                   ELSE 'LOW'
               END as risk_level,
               last_updated
        FROM violation_hotspots
        WHERE count >= ?
        ORDER BY count DESC
    """, (min_count,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_top_hotspot_zones(limit=10, violation_type=None):
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT location_name, SUM(count) as total, GROUP_CONCAT(DISTINCT violation_type) as types
        FROM violation_hotspots
    """
    params = []
    if violation_type:
        query += " WHERE violation_type=?"
        params.append(violation_type)
    query += " GROUP BY location_name ORDER BY total DESC LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# —————— Forecast Queries ——————

def save_forecast(forecast_date, violation_type, predicted_count, confidence, peak_hours, recommendation):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO forecasts (forecast_date, violation_type, predicted_count, confidence, peak_hours, recommendation, generated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (forecast_date, violation_type, predicted_count, confidence, peak_hours, recommendation, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_forecasts(limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM forecasts
        WHERE forecast_date >= DATE('now')
        ORDER BY forecast_date ASC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# —————— Report Queries ——————

def save_report(report_type, title, summary, file_path):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reports (report_type, title, summary, generated_at, file_path)
        VALUES (?, ?, ?, ?, ?)
    """, (report_type, title, summary, datetime.now().isoformat(), file_path))
    conn.commit()
    report_id = cursor.lastrowid
    conn.close()
    return report_id


def get_reports(limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM reports ORDER BY generated_at DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
