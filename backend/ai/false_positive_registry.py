"""False Positive Registry for TRINETRA AI.

Tracks and analyzes violations flagged as potential false positives,
enabling root-cause analysis and weekly accuracy reporting.

Schema:
    image_path: str — original image filename
    violation_type: str — e.g. 'NO_HELMET', 'WRONG_SIDE_DRIVING'
    confidence: float — confidence score at time of detection
    review_status: str — 'pending', 'confirmed_fp', 'confirmed_correct'
    review_notes: str — officer notes on why it was FP
    root_cause: str — e.g. 'motion_validation_missing', 'hsv_fallback'
    timestamp: str — ISO timestamp
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

TABLE_NAME = 'false_positive_registry'
REPORTS_DIR = 'reports'


def _get_db_path():
    """Get the database path from config or default."""
    try:
        import config
        return config.DB_PATH
    except Exception:
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'database.db')


def _ensure_table(conn):
    conn.execute(f'''
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT,
            violation_type TEXT,
            confidence REAL,
            review_status TEXT DEFAULT 'pending',
            review_notes TEXT DEFAULT '',
            root_cause TEXT DEFAULT '',
            timestamp TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')
    conn.commit()


def register_candidate(image_path, violation_type, confidence, root_cause=''):
    """Register a potential false positive for review tracking.

    Args:
        image_path: original image filename
        violation_type: type of violation
        confidence: confidence score
        root_cause: suspected root cause string
    """
    try:
        conn = sqlite3.connect(_get_db_path())
        _ensure_table(conn)
        conn.execute(
            f'''INSERT INTO {TABLE_NAME}
                (image_path, violation_type, confidence, root_cause, timestamp)
                VALUES (?, ?, ?, ?, ?)''',
            (os.path.basename(image_path), violation_type, confidence,
             root_cause, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f'Failed to register false positive candidate: {e}')


def mark_reviewed(record_id, status, notes=''):
    """Mark a registry entry as reviewed.

    Args:
        record_id: row id
        status: 'confirmed_fp' or 'confirmed_correct'
        notes: officer notes
    """
    try:
        conn = sqlite3.connect(_get_db_path())
        _ensure_table(conn)
        conn.execute(
            f'''UPDATE {TABLE_NAME}
                SET review_status=?, review_notes=?
                WHERE id=?''',
            (status, notes, record_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f'Failed to update false positive record: {e}')


def get_pending_reviews(limit=50):
    """Get all pending false positive candidates."""
    try:
        conn = sqlite3.connect(_get_db_path())
        _ensure_table(conn)
        cur = conn.execute(
            f'''SELECT id, image_path, violation_type, confidence,
                       root_cause, timestamp
                FROM {TABLE_NAME}
                WHERE review_status='pending'
                ORDER BY confidence DESC
                LIMIT ?''',
            (limit,)
        )
        rows = cur.fetchall()
        conn.close()
        return [
            {
                'id': r[0], 'image': r[1], 'violation_type': r[2],
                'confidence': r[3], 'root_cause': r[4], 'timestamp': r[5],
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f'Failed to query false positive registry: {e}')
        return []


def weekly_report():
    """Generate weekly false positive statistics.

    Returns:
        dict with weekly stats
    """
    try:
        conn = sqlite3.connect(_get_db_path())
        _ensure_table(conn)
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()

        # Total candidates this week
        cur = conn.execute(
            f'''SELECT COUNT(*) FROM {TABLE_NAME}
                WHERE created_at >= ?''',
            (week_ago,)
        )
        total_week = cur.fetchone()[0]

        # FP rate
        cur = conn.execute(
            f'''SELECT review_status, COUNT(*) FROM {TABLE_NAME}
                WHERE created_at >= ? AND review_status != 'pending'
                GROUP BY review_status''',
            (week_ago,)
        )
        reviewed = dict(cur.fetchall())

        # By violation type
        cur = conn.execute(
            f'''SELECT violation_type, COUNT(*) FROM {TABLE_NAME}
                WHERE created_at >= ?
                GROUP BY violation_type
                ORDER BY COUNT(*) DESC''',
            (week_ago,)
        )
        by_type = dict(cur.fetchall())

        # Top root causes
        cur = conn.execute(
            f'''SELECT root_cause, COUNT(*) FROM {TABLE_NAME}
                WHERE created_at >= ? AND root_cause != ''
                GROUP BY root_cause
                ORDER BY COUNT(*) DESC
                LIMIT 10''',
            (week_ago,)
        )
        top_causes = dict(cur.fetchall())

        conn.close()

        fp_count = reviewed.get('confirmed_fp', 0)
        correct_count = reviewed.get('confirmed_correct', 0)
        total_reviewed = fp_count + correct_count

        return {
            'total_candidates': total_week,
            'reviewed': total_reviewed,
            'confirmed_false_positives': fp_count,
            'confirmed_correct': correct_count,
            'fp_rate': round(fp_count / total_reviewed, 3) if total_reviewed > 0 else 0,
            'by_violation_type': by_type,
            'top_root_causes': top_causes,
            'period': 'last_7_days',
        }
    except Exception as e:
        logger.error(f'Failed to generate weekly report: {e}')
        return {'error': str(e)}


def get_accuracy_summary():
    """Produce overall accuracy summary from the registry.

    Returns:
        dict with accuracy stats
    """
    try:
        conn = sqlite3.connect(_get_db_path())
        _ensure_table(conn)

        cur = conn.execute(
            f'''SELECT review_status, COUNT(*) FROM {TABLE_NAME}
                WHERE review_status != 'pending'
                GROUP BY review_status'''
        )
        reviewed = dict(cur.fetchall())

        cur = conn.execute(f'SELECT COUNT(*) FROM {TABLE_NAME}')
        total = cur.fetchone()[0]

        fp = reviewed.get('confirmed_fp', 0)
        correct = reviewed.get('confirmed_correct', 0)
        reviewed_total = fp + correct

        conn.close()

        return {
            'total_tracked': total,
            'total_reviewed': reviewed_total,
            'confirmed_false_positives': fp,
            'confirmed_correct': correct,
            'fp_rate': round(fp / reviewed_total, 3) if reviewed_total > 0 else 0,
            'accuracy': round(correct / reviewed_total, 3) if reviewed_total > 0 else 0,
        }
    except Exception as e:
        return {'error': str(e)}
