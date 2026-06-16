import os, sys, pytest, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from database.models import ViolationRecord
from ai.detector import ObjectDetector
import config

_test_db = tempfile.mktemp(suffix='.db')


@pytest.fixture(autouse=True)
def test_db():
    orig = config.DB_PATH
    config.DB_PATH = _test_db
    from database.db import init_db
    init_db()
    yield
    config.DB_PATH = orig
    if os.path.exists(_test_db):
        os.remove(_test_db)


@pytest.fixture
def client():
    from main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def detector():
    return ObjectDetector()


@pytest.fixture
def sample_image():
    import cv2
    import numpy as np
    img = np.ones((480, 640, 3), dtype=np.uint8) * 60
    cv2.rectangle(img, (200, 300), (400, 600), (100, 120, 200), -1)
    cv2.rectangle(img, (250, 200), (350, 300), (80, 100, 180), -1)
    return img
