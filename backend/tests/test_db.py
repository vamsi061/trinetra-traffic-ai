import pytest
import os, sys
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.db import (
    init_db, get_connection,
    insert_violation, get_all_violations,
    get_recent_violations, get_statistics,
    get_violations_by_type, get_violations_by_day,
    get_top_repeat_offenders, get_monthly_trend,
)
from database.models import ViolationRecord


def make_record(vtype="NO_HELMET", vnum="", ts=None):
    return ViolationRecord(
        vehicle_number=vnum,
        vehicle_type="motorcycle",
        violation_type=vtype,
        confidence=0.9,
        image_path="/tmp/test.jpg",
        evidence_path="/tmp/ev.jpg",
        timestamp=ts or datetime.now().isoformat(),
    )


class TestDatabase:
    def test_init_db_creates_table(self):
        conn = get_connection()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        assert 'violations' in [t[0] for t in tables]
        conn.close()

    def test_insert_and_count(self):
        insert_violation(make_record())
        stats = get_statistics()
        assert stats['total'] >= 1
        assert stats['no_helmet'] >= 1

    def test_insert_multiple_types(self):
        insert_violation(make_record("NO_HELMET"))
        insert_violation(make_record("TRIPLE_RIDING"))
        stats = get_statistics()
        assert stats['total'] >= 2
        assert stats['no_helmet'] >= 1
        assert stats['triple_riding'] >= 1

    def test_get_all_violations(self):
        insert_violation(make_record())
        insert_violation(make_record("TRIPLE_RIDING"))
        results = get_all_violations()
        assert len(results) >= 2

    def test_get_all_violations_filter_type(self):
        insert_violation(make_record("NO_HELMET"))
        insert_violation(make_record("TRIPLE_RIDING"))
        nh = get_all_violations(violation_type="NO_HELMET")
        assert all(v.violation_type == "NO_HELMET" for v in nh)

    def test_get_all_violations_filter_vehicle(self):
        insert_violation(make_record(vnum="KA01AB1234"))
        insert_violation(make_record(vnum="MH12DE3456"))
        results = get_all_violations(vehicle_number="KA01")
        assert len(results) >= 1
        assert all("KA01" in v.vehicle_number for v in results)

    def test_get_recent_violations(self):
        for i in range(5):
            insert_violation(make_record())
        recent = get_recent_violations(3)
        assert len(recent) <= 3
        assert len(recent) > 0

    def test_get_statistics(self):
        insert_violation(make_record("NO_HELMET"))
        insert_violation(make_record("NO_HELMET"))
        insert_violation(make_record("TRIPLE_RIDING"))
        insert_violation(make_record("TRIPLE_RIDING", vnum="KA01AB1234"))
        stats = get_statistics()
        assert stats['total'] >= 4
        assert stats['no_helmet'] >= 2
        assert stats['triple_riding'] >= 2
        assert stats['unique_vehicles'] >= 1

    def test_get_violations_by_type(self):
        insert_violation(make_record("NO_HELMET"))
        insert_violation(make_record("TRIPLE_RIDING"))
        by_type = get_violations_by_type()
        types = {t['type']: t['count'] for t in by_type}
        assert 'NO_HELMET' in types
        assert 'TRIPLE_RIDING' in types

    def test_get_violations_by_day(self):
        insert_violation(make_record())
        by_day = get_violations_by_day()
        assert len(by_day) > 0
        assert 'day' in by_day[0]
        assert 'count' in by_day[0]

    def test_repeat_offenders(self):
        insert_violation(make_record(vnum="KA01AB1234"))
        insert_violation(make_record("TRIPLE_RIDING", vnum="KA01AB1234"))
        offenders = get_top_repeat_offenders()
        assert len(offenders) > 0
        assert any(o['vehicle'] == "KA01AB1234" for o in offenders)

    def test_monthly_trend(self):
        insert_violation(make_record())
        trend = get_monthly_trend()
        assert len(trend) > 0
        assert 'month' in trend[0]
        assert 'count' in trend[0]

    def test_violation_record_to_dict(self):
        v = ViolationRecord(id=1, vehicle_number="KA01AB1234",
                            violation_type="NO_HELMET", confidence=0.95)
        d = v.to_dict()
        assert d['id'] == 1
        assert d['vehicle_number'] == "KA01AB1234"
        assert d['violation_type'] == "NO_HELMET"
        assert d['confidence'] == 0.95

    def test_duplicate_insert(self):
        r = make_record()
        insert_violation(r)
        insert_violation(r)
        stats = get_statistics()
        assert stats['total'] >= 2
