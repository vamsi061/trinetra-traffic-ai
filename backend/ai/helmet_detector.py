"""TRINETRA AI — Production Helmet Detection Service.

Uses YOLOv8n fine-tuned for helmet detection (helmet_yolov8n.pt).
Fallback: HSV color thresholding when model unavailable.

Model classes:
  0: 'With Helmet'
  1: 'Without Helmet'

Pipeline:
  Image → Motorcycle Detection → Person Detection →
  Helmet Model Inference → Associate Helmets to Riders →
  HELMET_PRESENT | HELMET_MISSING | HELMET_UNKNOWN
"""

import cv2
import numpy as np
import os
import logging
from ai.rider_association import associate_riders
import config

logger = logging.getLogger(__name__)

HELMET_STATE_PRESENT = 'HELMET_PRESENT'
HELMET_STATE_ABSENT = 'NO_HELMET'
HELMET_STATE_UNKNOWN = 'HELMET_UNKNOWN'

HELMET_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'helmet_yolov8n.pt')


class HelmetDetectorService:
    """Singleton service for YOLO-based helmet detection with HSV fallback."""

    _instance = None
    _model = None
    _model_loaded = False
    _model_name = ''

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def load_model(self):
        """Load the YOLO helmet detection model."""
        if self._model_loaded:
            return True

        model_path = HELMET_MODEL_PATH
        if not os.path.exists(model_path):
            logger.warning(f"Helmet model not found at {model_path}")
            self._model_loaded = False
            self._model_name = 'unavailable'
            return False

        try:
            from ultralytics import YOLO
            self._model = YOLO(model_path)
            self._model_loaded = True
            self._model_name = 'helmet_yolov8n.pt'
            logger.info(f"Helmet model loaded: {model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load helmet model: {e}")
            self._model_loaded = False
            self._model_name = 'error'
            return False

    def is_available(self):
        """Check if the helmet model is loaded and available."""
        if not self._initialized:
            self.load_model()
            self._initialized = True
        return self._model_loaded

    def get_model_info(self):
        """Return diagnostic info about the helmet model."""
        if not self._initialized:
            self.load_model()
            self._initialized = True
        return {
            'loaded': self._model_loaded,
            'model_name': self._model_name,
            'beta': True,
            'classes': {0: 'With Helmet', 1: 'Without Helmet'} if self._model_loaded else {},
        }

    def detect(self, image):
        """Run YOLO helmet detection on the full image.

        Returns:
            list of dicts: {bbox, confidence, class_id, label}
              class_id 0 = With Helmet
              class_id 1 = Without Helmet
        """
        if not self.is_available():
            return []

        try:
            results = self._model(image, conf=0.25, iou=0.45, agnostic_nms=True)[0]
            detections = []
            if results.boxes is not None and len(results.boxes) > 0:
                boxes = results.boxes.xyxy.cpu().numpy()
                confs = results.boxes.conf.cpu().numpy()
                classes = results.boxes.cls.cpu().numpy().astype(int)
                for box, conf, cls_id in zip(boxes, confs, classes):
                    label = self._model.names.get(int(cls_id), f'class_{cls_id}')
                    detections.append({
                        'bbox': [float(x) for x in box],
                        'confidence': float(conf),
                        'class_id': int(cls_id),
                        'label': label,
                    })
            return detections
        except Exception as e:
            logger.error(f"Helmet model inference error: {e}")
            return []

    def get_status_string(self):
        """Return a human-readable status string for debug display."""
        if not self._initialized:
            self.load_model()
            self._initialized = True
        if self._model_loaded:
            return f"Helmet Model: {self._model_name} (Loaded)"
        else:
            return "Helmet Model: unavailable (using HSV fallback)"


# Global singleton
_helmet_service = None


def get_helmet_service():
    global _helmet_service
    if _helmet_service is None:
        _helmet_service = HelmetDetectorService()
        _helmet_service.load_model()
        _helmet_service._initialized = True
    return _helmet_service


# ====== HSV FALLBACK ======

def _hsv_helmet_detect(image, person_bbox):
    """HSV-based helmet detection — fallback when model unavailable.
    
    Returns:
        (state, confidence)
    """
    x1, y1, x2, y2 = [int(v) for v in person_bbox]
    person_h = y2 - y1
    person_w = x2 - x1

    if person_h < 20 or person_w < 10:
        return HELMET_STATE_UNKNOWN, 0.0

    # Analyze the upper portion of the head (top 25%) - enough to capture
    # the helmet crown while minimizing face interference.
    head_y2 = y1 + int(person_h * 0.25)
    head_region = image[y1:head_y2, x1:x2]

    if head_region.size == 0:
        return HELMET_STATE_UNKNOWN, 0.0

    h, w = head_region.shape[:2]
    total_pixels = h * w
    if total_pixels < 50:  # too small to analyze
        return HELMET_STATE_UNKNOWN, 0.0

    hsv = cv2.cvtColor(head_region, cv2.COLOR_BGR2HSV)

    # Edge density analysis: hair has many fine edges, helmets have few.
    # Pre-blur to suppress helmet surface texture while keeping hair edges.
    gray_head = cv2.cvtColor(head_region, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray_head, (5, 5), 0)
    edge_kernel = np.ones((3, 3), np.uint8)
    edges = cv2.Canny(blurred, 40, 120)
    edges = cv2.dilate(edges, edge_kernel, iterations=1)
    edge_density = cv2.countNonZero(edges) / total_pixels
    is_low_edge = edge_density < 0.25

    # CLAHE for lighting normalization
    hsv_eq = hsv
    try:
        if gray_head.std() > 15:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray_head)
            hsv_eq = cv2.cvtColor(cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR), cv2.COLOR_BGR2HSV)
    except Exception:
        pass

    kernel = np.ones((5, 5), np.uint8)
    max_blob_ratio = 0.0
    best_color = None

    for color_name, (lower, upper) in config.HELMET_COLORS_HSV.items():
        lower = np.array(lower, dtype=np.uint8)
        upper = np.array(upper, dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
        if num_labels > 1:
            largest_blob_area = np.max(stats[1:, cv2.CC_STAT_AREA])
            blob_ratio = largest_blob_area / total_pixels
        else:
            blob_ratio = 0.0

        if hsv_eq is not hsv:
            mask_eq = cv2.inRange(hsv_eq, lower, upper)
            mask_eq = cv2.morphologyEx(mask_eq, cv2.MORPH_CLOSE, kernel)
            mask_eq = cv2.morphologyEx(mask_eq, cv2.MORPH_OPEN, kernel)

            num_labels_eq, labels_eq, stats_eq, _ = cv2.connectedComponentsWithStats(mask_eq, connectivity=8)
            if num_labels_eq > 1:
                largest_blob_area_eq = np.max(stats_eq[1:, cv2.CC_STAT_AREA])
                blob_ratio_eq = largest_blob_area_eq / total_pixels
            else:
                blob_ratio_eq = 0.0
            blob_ratio = max(blob_ratio, blob_ratio_eq)

        if blob_ratio > max_blob_ratio:
            max_blob_ratio = blob_ratio
            best_color = color_name

    if is_low_edge:
        if max_blob_ratio > 0.12:
            return HELMET_STATE_PRESENT, min(max_blob_ratio * 1.2, 0.95)
        return HELMET_STATE_UNKNOWN, max(0.30, max_blob_ratio)

    return HELMET_STATE_ABSENT, min(0.70, max(0.40, 1.0 - edge_density))


# ====== MAIN HELMET VIOLATION CHECK ======

def _associate_helmet_to_rider(helmet_detections, person_bbox):
    """Check if a helmet detection is associated with a rider.
    
    A helmet belongs to a rider if:
    - Helmet bbox center lies inside rider upper-body region
    - OR helmet bbox overlaps rider head region significantly
    
    Returns:
        (is_associated, state, confidence)
    """
    px1, py1, px2, py2 = person_bbox
    p_cy = (py1 + py2) / 2
    person_h = py2 - py1

    # Rider upper body region (upper 50% of person bbox)
    upper_y2 = py1 + person_h * 0.50

    best_match = None
    best_iou = 0.0

    for hd in helmet_detections:
        hx1, hy1, hx2, hy2 = hd['bbox']
        h_cx = (hx1 + hx2) / 2
        h_cy = (hy1 + hy2) / 2

        # Check if helmet center is inside rider upper body
        if px1 <= h_cx <= px2 and py1 <= h_cy <= upper_y2:
            # Strong match — helmet center in rider's head area
            inter_x1 = max(px1, hx1)
            inter_y1 = max(py1, hy1)
            inter_x2 = min(px2, hx2)
            inter_y2 = min(py2, hy2)
            inter = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
            area_p = (px2 - px1) * (py2 - py1)
            area_h = (hx2 - hx1) * (hy2 - hy1)
            union = area_p + area_h - inter
            iou = inter / union if union > 0 else 0

            if iou > best_iou:
                best_iou = iou
                best_match = hd

    if best_match is not None:
        state = HELMET_STATE_PRESENT if best_match['class_id'] == 0 else HELMET_STATE_ABSENT
        return True, state, best_match['confidence']
    return False, None, 0.0


def check_helmet_violation(detections, image):
    """Check for helmet violations using YOLO helmet model + HSV fallback.
    
    Pipeline:
      1. Associate persons to motorcycles (riders)
      2. Run YOLO helmet model on full image
      3. Associate helmet detections to riders
      4. For riders without model association, use HSV fallback
      5. Generate violations for HELMET_MISSING
    
    Returns:
        list of violation dicts
    """
    persons = [d for d in detections if d['class_id'] == config.PERSON_CLASS_ID and d.get('confidence', 0) >= 0.25]
    motorcycles = [d for d in detections if d['class_id'] == config.MOTORCYCLE_CLASS_ID]

    if not persons or not motorcycles:
        return []

    img_shape = image.shape[:2] if image is not None else (None, None)
    associations = associate_riders(persons, motorcycles, img_shape)

    # Run YOLO helmet model on full image
    service = get_helmet_service()
    helmet_detections = service.detect(image)
    model_available = service.is_available()

    violations = []

    for assoc in associations:
        mc = assoc['motorcycle']
        for person in assoc['riders']:
            person_bbox = person['bbox']
            person_id = person.get('instance_id', 'unknown')

            # Step 1: Try YOLO model association
            model_checked_no_match = False
            if model_available and helmet_detections:
                is_associated, model_state, model_conf = _associate_helmet_to_rider(
                    helmet_detections, person_bbox
                )

                if is_associated:
                    # Model made a decision — use it
                    if model_state == HELMET_STATE_ABSENT:
                        severity = config.RISK_SCORES.get('NO_HELMET', 30)
                        violations.append(_make_violation(
                            person, mc, model_conf, HELMET_STATE_ABSENT, severity,
                            'Model-based detection: rider without associated helmet.'
                        ))
                    # If PRESENT, no violation needed
                    continue
                else:
                    model_checked_no_match = True

            # Step 2: No model association — try HSV fallback
            hsv_state, hsv_conf = _hsv_helmet_detect(image, person_bbox)

            if hsv_state == HELMET_STATE_ABSENT:
                # Confidently no helmet — flag as violation
                if model_available:
                    violations.append(_make_violation(
                        person, mc, hsv_conf, hsv_state, config.RISK_SCORES.get('NO_HELMET', 30),
                        'Helmet model: no matching detection. HSV analysis confirms no protective headgear.'
                    ))
                else:
                    violations.append(_make_violation(
                        person, mc, hsv_conf, hsv_state, config.RISK_SCORES.get('NO_HELMET', 30),
                        'HSV-based detection: rider without visible protective headgear.'
                    ))
            elif hsv_state == HELMET_STATE_UNKNOWN:
                # HSV uncertain — flag for review regardless of model availability
                violations.append(_make_violation(
                    person, mc, hsv_conf, hsv_state, max(15, config.RISK_SCORES.get('NO_HELMET', 30) - 10),
                    'Helmet model unavailable. HSV analysis uncertain. Human review required.'
                    if not model_available else
                    'Helmet model: no matching detection. HSV analysis suggests possible non-compliance.'
                ))

    # Log diagnostics
    logger.debug(
        f"Helmet check: model={'available' if model_available else 'unavailable'}, "
        f"model_detections={len(helmet_detections)}, "
        f"riders={sum(len(a['riders']) for a in associations)}, "
        f"violations={len(violations)}"
    )

    return violations


def _make_violation(person, mc, confidence, helmet_state, severity, reason):
    """Build a violation dict."""
    return {
        'violation_type': 'NO_HELMET',
        'confidence': round(confidence, 3),
        'helmet_state': helmet_state,
        'helmet_confidence': round(confidence, 3),
        'person_bbox': person['bbox'],
        'motorcycle_bbox': mc['bbox'],
        'severity_score': severity,
        'description': f'{person.get("instance_id", "Rider")} without helmet on {mc.get("instance_id", "motorcycle")}',
        'involved_objects': [
            person.get('instance_id', 'person'),
            mc.get('instance_id', 'motorcycle'),
        ],
        'helmet_reason': reason,
    }
