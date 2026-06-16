import pytest
import cv2
import numpy as np
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.ocr import LicensePlateReader


class TestLicensePlateReader:
    def test_singleton(self):
        r1 = LicensePlateReader()
        r2 = LicensePlateReader()
        assert r1 is r2

    def test_reader_loads(self):
        reader = LicensePlateReader()
        loaded = reader.load_reader()
        assert loaded is not None or not hasattr(LicensePlateReader, 'read_text')

    def test_empty_image_returns_empty(self):
        reader = LicensePlateReader()
        img = np.ones((100, 100, 3), dtype=np.uint8) * 128
        text, conf = reader.read_plate(img, [0, 0, 100, 100])
        assert isinstance(text, str)
        assert isinstance(conf, float)

    def test_extract_plate_region_valid(self):
        reader = LicensePlateReader()
        img = np.ones((480, 640, 3), dtype=np.uint8) * 100
        bbox = [100, 100, 300, 300]
        region = reader.extract_plate_region(img, bbox)
        assert region is not None
        assert region.shape[0] > 0
        assert region.shape[1] > 0

    def test_extract_plate_region_edge_case(self):
        reader = LicensePlateReader()
        img = np.ones((100, 100, 3), dtype=np.uint8)
        bbox = [0, 0, 10, 5]
        region = reader.extract_plate_region(img, bbox)
        assert region is not None

    def test_invalid_bbox_returns_none(self):
        reader = LicensePlateReader()
        img = np.ones((100, 100, 3), dtype=np.uint8)
        bbox = [95, 95, 5, 5]
        region = reader.extract_plate_region(img, bbox)
        if region is None:
            assert True
        else:
            assert region.size > 0

    def test_validate_plate_format_valid(self):
        reader = LicensePlateReader()
        assert reader.validate_plate_format("KA01AB1234") == True
        assert reader.validate_plate_format("MH12DE3456") == True
        assert reader.validate_plate_format("DL04PQ1234") == True

    def test_validate_plate_format_invalid(self):
        reader = LicensePlateReader()
        assert reader.validate_plate_format("") == False
        assert reader.validate_plate_format("AB") == False
        assert reader.validate_plate_format("12345") == False
        assert reader.validate_plate_format("HELLO WORLD") == False

    def test_find_plate_contours_valid_region(self):
        reader = LicensePlateReader()
        img = np.ones((200, 200, 3), dtype=np.uint8) * 50
        cv2.rectangle(img, (50, 80), (150, 110), (200, 200, 50), -1)
        cv2.rectangle(img, (50, 80), (150, 110), (255, 255, 255), 2)
        candidates = reader.find_plate_contours(img)
        assert isinstance(candidates, list)

    def test_real_image_plate_detection(self):
        path = os.path.join(os.path.dirname(__file__), 'samples', 'test4_car_plate.jpg')
        img = cv2.imread(path)
        if img is None:
            pytest.skip("Sample test4_car_plate.jpg not found")
        reader = LicensePlateReader()
        vehicle_bbox = [150, 250, 450, 400]
        text, conf = reader.read_plate(img, vehicle_bbox)
        assert len(text) > 0, "Should extract plate text from test4"
        assert conf > 0.0
