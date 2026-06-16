import pytest
import cv2
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.wrong_side_detector import (
    detect_lane_lines, classify_lane_lines,
    get_average_lane_angle, is_vehicle_wrong_side,
    check_wrong_side_violation
)


class TestWrongSideDetection:
    def test_detect_lane_lines_returns_list_or_none(self):
        img = np.ones((480, 640, 3), dtype=np.uint8) * 60
        cv2.line(img, (100, 400), (300, 200), (255, 255, 255), 5)
        cv2.line(img, (500, 400), (350, 200), (255, 255, 255), 5)
        lines = detect_lane_lines(img)
        assert lines is None or len(lines) > 0

    def test_classify_lane_lines_empty(self):
        left, right = classify_lane_lines(None, 640)
        assert len(left) == 0
        assert len(right) == 0

    def test_get_average_angle_none(self):
        assert get_average_lane_angle([]) is None
        assert get_average_lane_angle(None) is None

    def test_is_vehicle_wrong_side_no_lanes(self):
        wrong, conf = is_vehicle_wrong_side([0, 0, 100, 100], [], [], 640)
        assert wrong == False
        assert conf == 0.0

    def test_check_no_violation_no_vehicles(self):
        img = np.ones((480, 640, 3), dtype=np.uint8) * 60
        violations = check_wrong_side_violation([], img)
        assert len(violations) == 0

    def test_check_no_violation_no_lanes(self):
        img = np.ones((480, 640, 3), dtype=np.uint8) * 60
        detections = [
            {'bbox': [100, 200, 300, 400], 'confidence': 0.9, 'class_id': 2, 'label': 'car'},
        ]
        violations = check_wrong_side_violation(detections, img)
        assert len(violations) == 0
