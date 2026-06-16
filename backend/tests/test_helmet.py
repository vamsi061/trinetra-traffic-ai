import pytest
import cv2
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.helmet_detector import (
    detect_helmet_in_head_region, check_helmet_violation
)
from ai.rider_association import is_person_on_motorcycle


def iou(box1, box2):
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0
from ai.detector import ObjectDetector
import config


class TestHelmetUtilities:
    def test_iou_identical_boxes(self):
        box = [0, 0, 100, 100]
        assert iou(box, box) == 1.0

    def test_iou_no_overlap(self):
        box1 = [0, 0, 10, 10]
        box2 = [100, 100, 110, 110]
        assert iou(box1, box2) == 0.0

    def test_iou_partial_overlap(self):
        box1 = [0, 0, 100, 100]
        box2 = [50, 50, 150, 150]
        val = iou(box1, box2)
        assert 0.1 < val < 0.9

    def test_iou_zero_area(self):
        assert iou([0, 0, 0, 0], [0, 0, 10, 10]) == 0.0

    def test_person_on_motorcycle_true(self):
        person = [100, 200, 140, 300]
        bike = [90, 180, 200, 320]
        assert is_person_on_motorcycle(person, bike) == True

    def test_person_on_motorcycle_false(self):
        person = [0, 0, 30, 60]
        bike = [300, 300, 400, 400]
        assert is_person_on_motorcycle(person, bike) == False


class TestHelmetDetection:
    def test_detect_helmet_white(self):
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        person_bbox = [0, 0, 100, 100]
        has_helmet, _ = detect_helmet_in_head_region(img, person_bbox)
        assert has_helmet == True

    def test_detect_helmet_black(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        person_bbox = [0, 0, 100, 100]
        has_helmet, _ = detect_helmet_in_head_region(img, person_bbox)
        assert has_helmet == True

    def test_detect_helmet_absent(self):
        img = np.ones((100, 100, 3), dtype=np.uint8) * 50
        img[:, :] = (80, 180, 80)  # green, not matching any helmet color range
        person_bbox = [0, 0, 100, 100]
        has_helmet, _ = detect_helmet_in_head_region(img, person_bbox)
        assert has_helmet == False

    def test_empty_head_region(self):
        img = np.ones((10, 10, 3), dtype=np.uint8)
        person_bbox = [0, 0, 5, 2]
        has_helmet, _ = detect_helmet_in_head_region(img, person_bbox)
        assert has_helmet == False

    def test_check_no_violation_with_helmet(self):
        img = np.ones((200, 200, 3), dtype=np.uint8) * 255
        detections = [
            {'bbox': [50, 50, 100, 180], 'confidence': 0.9, 'class_id': 0, 'label': 'person', 'instance_id': 'person_1'},
            {'bbox': [40, 100, 160, 190], 'confidence': 0.85, 'class_id': 3, 'label': 'motorcycle', 'instance_id': 'motorcycle_1'},
        ]
        violations = check_helmet_violation(detections, img)
        assert len(violations) == 0

    def test_check_violation_no_helmet(self):
        img = np.ones((200, 200, 3), dtype=np.uint8) * 50
        img[:, :] = (80, 180, 80)  # green, not matching any helmet color
        detections = [
            {'bbox': [50, 50, 100, 180], 'confidence': 0.9, 'class_id': 0, 'label': 'person', 'instance_id': 'person_1'},
            {'bbox': [40, 100, 160, 190], 'confidence': 0.85, 'class_id': 3, 'label': 'motorcycle', 'instance_id': 'motorcycle_1'},
        ]
        violations = check_helmet_violation(detections, img)
        assert len(violations) >= 1
        assert violations[0]['violation_type'] == 'NO_HELMET'

    def test_no_motorcycle_no_violation(self):
        img = np.ones((200, 200, 3), dtype=np.uint8) * 100
        detections = [
            {'bbox': [50, 50, 100, 180], 'confidence': 0.9, 'class_id': 0, 'label': 'person'},
        ]
        violations = check_helmet_violation(detections, img)
        assert len(violations) == 0
