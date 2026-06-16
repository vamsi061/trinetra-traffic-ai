import pytest
import cv2
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.detector import ObjectDetector


class TestDetector:
    def test_model_loads(self, detector):
        model = detector.load_model()
        assert model is not None

    def test_detect_returns_list(self, detector, sample_image):
        results = detector.detect(sample_image)
        assert isinstance(results, list)

    def test_detection_has_required_keys(self, detector, sample_image):
        results = detector.detect(sample_image)
        for r in results:
            assert 'bbox' in r
            assert 'confidence' in r
            assert 'class_id' in r
            assert 'label' in r
            assert len(r['bbox']) == 4

    def test_confidence_in_range(self, detector, sample_image):
        results = detector.detect(sample_image)
        for r in results:
            assert 0.0 <= r['confidence'] <= 1.0

    def test_detect_vehicles_filter(self, detector):
        dets = detector.detect_vehicles(np.ones((480, 640, 3), dtype=np.uint8) * 60)
        for v in dets:
            assert v['class_id'] in [2, 3, 5, 7]
            assert 'vehicle_type' in v

    def test_detect_persons_filter(self, detector):
        persons = detector.detect_persons(np.ones((480, 640, 3), dtype=np.uint8) * 60)
        for p in persons:
            assert p['class_id'] == 0

    def test_detect_motorcycles_filter(self, detector):
        bikes = detector.detect_motorcycles(np.ones((480, 640, 3), dtype=np.uint8) * 60)
        for b in bikes:
            assert b['class_id'] == 3

    def test_singleton_pattern(self):
        d1 = ObjectDetector()
        d2 = ObjectDetector()
        assert d1 is d2


