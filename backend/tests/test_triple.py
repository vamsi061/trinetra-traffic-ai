import pytest
import cv2
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.triple_riding import check_triple_riding
from ai.detector import ObjectDetector


class TestTripleRiding:
    def _actual_violations(self, violations):
        # Filter out NORMAL labels — only count actual violations
        return [v for v in violations if v['violation_type'] not in ('NORMAL', 'NO_OCCUPANTS')]

    def test_no_violation_one_rider(self):
        detections = [
            {'bbox': [50, 50, 100, 180], 'confidence': 0.9, 'class_id': 0, 'label': 'person'},
            {'bbox': [40, 100, 160, 190], 'confidence': 0.85, 'class_id': 3, 'label': 'motorcycle'},
        ]
        violations = check_triple_riding(detections)
        assert len(self._actual_violations(violations)) == 0
        assert any(v['violation_type'] == 'NORMAL' for v in violations)

    def test_no_violation_two_riders(self):
        detections = [
            {'bbox': [50, 50, 100, 180], 'confidence': 0.9, 'class_id': 0, 'label': 'person'},
            {'bbox': [60, 55, 110, 175], 'confidence': 0.85, 'class_id': 0, 'label': 'person'},
            {'bbox': [40, 100, 160, 190], 'confidence': 0.85, 'class_id': 3, 'label': 'motorcycle'},
        ]
        violations = check_triple_riding(detections)
        assert len(self._actual_violations(violations)) == 0
        assert any(v['violation_type'] == 'NORMAL' for v in violations)

    def test_violation_three_riders(self):
        detections = [
            {'bbox': [50, 50, 100, 180], 'confidence': 0.9, 'class_id': 0, 'label': 'person'},
            {'bbox': [60, 55, 110, 175], 'confidence': 0.85, 'class_id': 0, 'label': 'person'},
            {'bbox': [45, 60, 105, 170], 'confidence': 0.8, 'class_id': 0, 'label': 'person'},
            {'bbox': [40, 100, 160, 190], 'confidence': 0.85, 'class_id': 3, 'label': 'motorcycle'},
        ]
        violations = check_triple_riding(detections)
        actual = self._actual_violations(violations)
        assert len(actual) >= 1
        assert actual[0]['violation_type'] == 'TRIPLE_RIDING'
        assert actual[0]['rider_count'] >= 3

    def test_no_motorcycle_no_violation(self):
        detections = [
            {'bbox': [50, 50, 100, 180], 'confidence': 0.9, 'class_id': 0, 'label': 'person'},
            {'bbox': [60, 55, 110, 175], 'confidence': 0.85, 'class_id': 0, 'label': 'person'},
        ]
        violations = check_triple_riding(detections)
        assert len(violations) == 0


