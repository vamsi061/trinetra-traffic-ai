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
    conn.commit()
    conn.close()


def insert_violation(record):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO violations
            (vehicle_number, vehicle_type, violation_type,
             confidence, image_path, evidence_path, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        record.vehicle_number,
        record.vehicle_type,
        record.violation_type,
        record.confidence,
        record.image_path,
        record.evidence_path,
        record.timestamp,
    ))
    conn.commit()
    conn.close()


def get_all_violations(vehicle_number=None, violation_type=None, date_from=None, date_to=None):
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
    cursor.execute("SELECT COUNT(DISTINCT vehicle_number) FROM violations WHERE vehicle_number != ''")
    stats['unique_vehicles'] = cursor.fetchone()[0]
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
