import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get('DATA_DIR', os.path.join(BASE_DIR, 'data'))
UPLOAD_DIR = os.path.join(DATA_DIR, 'uploads')
EVIDENCE_DIR = os.path.join(DATA_DIR, 'evidence')
DB_PATH = os.path.join(DATA_DIR, 'database.db')

YOLO_MODEL_NAME = 'yolov8s.pt'
CONFIDENCE_THRESHOLD = 0.25
AGNOSTIC_NMS = True
OCR_CONFIDENCE_THRESHOLD = 0.3
LANE_ANGLE_THRESHOLD = 25
OVERLOADING_THRESHOLD = 4
VEHICLE_CONFIDENCE_THRESHOLD = 0.60

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
    9: 'traffic light',
    11: 'stop sign',
}

VIOLATION_TYPES = {
    'NO_HELMET': 'No Helmet',
    'HELMET_ASSESSMENT_UNCERTAIN': 'Possible Helmet Non-Compliance',
    'TRIPLE_RIDING': 'Triple Riding',
    'MOTORCYCLE_OVERLOADING': 'Motorcycle Overloading',
    'MOTORCYCLE_EXTREME_OVERLOADING': 'Extreme Overloading',
    'SEATBELT_VIOLATION': 'Seatbelt Violation',
    'WRONG_SIDE_DRIVING': 'Wrong Side Driving',
    'RED_LIGHT_VIOLATION': 'Red Light Violation',
    'STOP_LINE_VIOLATION': 'Stop Line Violation',
}

RISK_SCORES = {
    'NO_HELMET': 30,
    'HELMET_ASSESSMENT_UNCERTAIN': 15,
    'TRIPLE_RIDING': 75,
    'MOTORCYCLE_OVERLOADING': 95,
    'MOTORCYCLE_EXTREME_OVERLOADING': 98,
    'SEATBELT_VIOLATION': 40,
    'WRONG_SIDE_DRIVING': 85,
    'RED_LIGHT_VIOLATION': 90,
    'STOP_LINE_VIOLATION': 60,
}

# Confidence thresholds
HIGH_CONFIDENCE = 0.80
MEDIUM_CONFIDENCE = 0.60
LOW_CONFIDENCE = 0.40

# Rider scoring weights
RIDER_DISTANCE_WEIGHT = 0.45
RIDER_VERTICAL_WEIGHT = 0.30
RIDER_HORIZONTAL_WEIGHT = 0.15
RIDER_OVERLAP_WEIGHT = 0.10

# Occupancy limits
MAX_REALISTIC_OCCUPANCY = 5

HELMET_COLORS_HSV = {
    'white': ([0, 0, 180], [180, 30, 255]),
    'black': ([0, 0, 0], [180, 255, 60]),
    'grey': ([0, 0, 60], [180, 30, 180]),
    'red': ([0, 50, 50], [10, 255, 255]),
    'blue': ([100, 50, 50], [130, 255, 255]),
    'yellow': ([20, 50, 50], [35, 255, 255]),
}

# —————— Risk Scoring Engine ——————
REPEAT_OFFENDER_MULTIPLIERS = {
    0: 1.0,      # First offence
    1: 1.5,      # 1 prior
    2: 2.0,      # 2 priors
    3: 2.5,      # 3 priors
    4: 3.0,      # 4+ priors
}

LOCATION_RISK_MULTIPLIERS = {
    'school_zone': 1.5,
    'hospital_zone': 1.4,
    'residential': 1.1,
    'highway': 1.3,
    'market': 1.2,
    'default': 1.0,
}

TIME_RISK_MULTIPLIERS = {
    'peak_morning': (7, 10, 1.3),
    'peak_evening': (16, 19, 1.3),
    'night': (22, 5, 1.2),
    'default': (0, 24, 1.0),
}

RISK_STATUS_THRESHOLDS = {
    'CRITICAL': 150,
    'HIGH': 80,
    'MEDIUM': 40,
    'LOW': 0,
}

# —————— Hotspot Analytics ——————
HOTSPOT_GRID_SIZE = 50  # meters
HOTSPOT_MIN_SAMPLES = 3

# —————— Forecast ——————
FORECAST_LOOKBACK_DAYS = 30
FORECAST_CONFIDENCE_DECAY = 0.95

# —————— Report Paths ——————
REPORT_DIR = os.path.join(DATA_DIR, 'reports')
