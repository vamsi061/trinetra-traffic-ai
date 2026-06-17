import sqlite3
from datetime import datetime


class ViolationRecord:
    def __init__(self, id=None, vehicle_number=None, vehicle_type=None,
                 violation_type=None, confidence=None, image_path=None,
                 evidence_path=None, location=None, timestamp=None):
        self.id = id
        self.vehicle_number = vehicle_number or ''
        self.vehicle_type = vehicle_type or ''
        self.violation_type = violation_type or ''
        self.confidence = confidence or 0.0
        self.image_path = image_path or ''
        self.evidence_path = evidence_path or ''
        self.location = location or ''
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self):
        return {
            'id': self.id,
            'vehicle_number': self.vehicle_number,
            'vehicle_type': self.vehicle_type,
            'violation_type': self.violation_type,
            'confidence': self.confidence,
            'image_path': self.image_path,
            'evidence_path': self.evidence_path,
            'location': self.location,
            'timestamp': self.timestamp,
        }

    @staticmethod
    def from_row(row):
        return ViolationRecord(
            id=row[0],
            vehicle_number=row[1],
            vehicle_type=row[2],
            violation_type=row[3],
            confidence=row[4],
            image_path=row[5],
            evidence_path=row[6],
            location=row[7] if len(row) > 7 else '',
            timestamp=row[8] if len(row) > 8 else row[7],
        )
