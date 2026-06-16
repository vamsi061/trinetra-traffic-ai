import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOAD_DIR = os.path.join(DATA_DIR, 'uploads')
EVIDENCE_DIR = os.path.join(DATA_DIR, 'evidence')
DB_PATH = os.path.join(DATA_DIR, 'database.db')

YOLO_MODEL_NAME = 'yolov8n.pt'
CONFIDENCE_THRESHOLD = 0.4
OCR_CONFIDENCE_THRESHOLD = 0.3
SEATBELT_IoU_THRESHOLD = 0.1
SEATBELT_LINE_THRESHOLD = 30
LANE_ANGLE_THRESHOLD = 25

VEHICLE_CLASSES = {
    2: 'car',
    3: 'motorcycle',
    5: 'bus',
    7: 'truck',
}

PERSON_CLASS_ID = 0
MOTORCYCLE_CLASS_ID = 3
CAR_CLASS_ID = 2

CLASS_NAMES = {
    0: 'person',
    1: 'bicycle',
    2: 'car',
    3: 'motorcycle',
    5: 'bus',
    7: 'truck',
}

VIOLATION_TYPES = {
    'NO_HELMET': 'No Helmet',
    'TRIPLE_RIDING': 'Triple Riding',
    'SEATBELT_VIOLATION': 'Seatbelt Violation',
    'WRONG_SIDE_DRIVING': 'Wrong-Side Driving',
}

HELMET_COLORS_HSV = {
    'white': ([0, 0, 180], [180, 30, 255]),
    'black': ([0, 0, 0], [180, 255, 60]),
    'grey': ([0, 0, 60], [180, 30, 180]),
    'red': ([0, 50, 50], [10, 255, 255]),
    'blue': ([100, 50, 50], [130, 255, 255]),
    'yellow': ([20, 50, 50], [35, 255, 255]),
}
