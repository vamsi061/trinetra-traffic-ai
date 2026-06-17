import pytest
import cv2
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.seatbelt_detector import (
    iou, is_person_in_car,
    detect_seatbelt_in_torso, check_seatbelt_violation
)
from ai.detector import ObjectDetector


class TestSeatbeltUtilities:
    def test_iou_identical(self):
        assert iou([0, 0, 100, 100], [0, 0, 100, 100]) == 1.0

    def test_iou_no_overlap(self):
        assert iou([0, 0, 10, 10], [100, 100, 110, 110]) == 0.0

    def test_person_in_car_true(self):
        person = [50, 50, 100, 180]
        car = [30, 40, 200, 220]
        assert is_person_in_car(person, car) == True

    def test_person_in_car_false(self):
        person = [310, 350, 330, 400]   # person below car, clearly not inside
        car = [100, 100, 250, 250]
        assert is_person_in_car(person, car) == False


class TestSeatbeltDetection:
    def test_torso_with_diagonal_lines_returns_true(self):
        img = np.ones((200, 200, 3), dtype=np.uint8) * 100
        cv2.line(img, (30, 50), (70, 100), (200, 200, 200), 3)
        person_bbox = [0, 0, 100, 200]
        result = detect_seatbelt_in_torso(img, person_bbox)
        assert result == True

    def test_torso_no_lines_returns_false(self):
        img = np.ones((200, 200, 3), dtype=np.uint8) * 100
        person_bbox = [0, 0, 100, 200]
        result = detect_seatbelt_in_torso(img, person_bbox)
        assert result == False

    def test_tiny_region_returns_none(self):
        img = np.ones((10, 10, 3), dtype=np.uint8)
        person_bbox = [0, 0, 5, 5]
        result = detect_seatbelt_in_torso(img, person_bbox)
        assert result is None

    def test_check_seatbelt_violation_no_car(self):
        img = np.ones((200, 200, 3), dtype=np.uint8) * 100
        detections = [
            {'bbox': [50, 50, 100, 180], 'confidence': 0.9, 'class_id': 0, 'label': 'person'},
        ]
        violations = check_seatbelt_violation(detections, img)
        assert len(violations) == 0

    def test_check_seatbelt_violation_with_car_no_belt(self):
        img = np.ones((200, 200, 3), dtype=np.uint8) * 100
        detections = [
            {'bbox': [50, 50, 100, 180], 'confidence': 0.9, 'class_id': 0, 'label': 'person'},
            {'bbox': [30, 40, 200, 220], 'confidence': 0.85, 'class_id': 2, 'label': 'car'},
        ]
        violations = check_seatbelt_violation(detections, img)
        assert len(violations) >= 1
        assert violations[0]['violation_type'] == 'SEATBELT_VIOLATION'
