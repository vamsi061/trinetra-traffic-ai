"""TRINETRA AI — Production Helmet Detection Service v5.

Architecture:
  For each associated rider:
    1. Crop rider bbox from ORIGINAL image with expansion (L/R 15%, top 25%, bottom 10%)
    2. Resize crop to 640x640 with aspect ratio preservation
    3. Run helmet_yolov8n.pt on the crop (native imgsz=224)
    4. Determine WITH_HELMET / WITHOUT_HELMET / HELMET_UNKNOWN

  HSV is emergency fallback only (confidence capped at 0.55).
  HELMET_UNKNOWN never converts to NO_HELMET.
  NO_HELMET requires model class=WITHOUT_HELMET AND confidence >= 0.55.

Model classes:
  0: 'With Helmet'
  1: 'Without Helmet'
"""

import cv2
import numpy as np
import os
import json
import logging
import time
from ai.rider_association import associate_riders
import config

logger = logging.getLogger(__name__)

HELMET_STATE_PRESENT = 'HELMET_PRESENT'
HELMET_STATE_ABSENT = 'NO_HELMET'
HELMET_STATE_UNKNOWN = 'HELMET_UNKNOWN'

HELMET_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'helmet_yolov8n.pt')

DEBUG_DIR = os.path.join(config.DATA_DIR, 'helmet_crop_debug')

CROP_TARGET_SIZE = 640
CROP_MIN_SIZE = 320
NO_HELMET_THRESHOLD = 0.55
HELMET_LOW_CONF_THRESHOLD = 0.40
MODEL_IMGSZ = 224

# Head area filter: skip riders whose estimated head size is below threshold
# Head area = person_bbox_width * person_bbox_height * HEAD_AREA_RATIO
# Calibrated for YOLO bboxes (which can be narrower than ground-truth).
# MIN_HEAD_AREA=2000 covers all known TP riders (min YOLO head_area=2126)
# while filtering very distant/small riders (<50px tall) that are always FP.
MIN_HEAD_AREA = 2000
HEAD_AREA_RATIO = 0.25

# Bbox expansion ratios
EXPAND_LEFT = 0.15
EXPAND_RIGHT = 0.15
EXPAND_TOP = 0.25
EXPAND_BOTTOM = 0.10

os.makedirs(DEBUG_DIR, exist_ok=True)


class HelmetDetectorService:
    """Singleton service for crop-based YOLO helmet detection with HSV emergency fallback."""

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
        if not self._initialized:
            self.load_model()
            self._initialized = True
        return self._model_loaded

    def get_model_info(self):
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
        if not self._initialized:
            self.load_model()
            self._initialized = True
        if self._model_loaded:
            return f"Helmet Model: {self._model_name} (Loaded)"
        else:
            return "Helmet Model: unavailable (using HSV fallback)"


_helmet_service = None


def get_helmet_service():
    global _helmet_service
    if _helmet_service is None:
        _helmet_service = HelmetDetectorService()
        _helmet_service.load_model()
        _helmet_service._initialized = True
    return _helmet_service


# ====== CROP & RESIZE ======

def _expand_bbox(bbox, img_shape):
    x1, y1, x2, y2 = [int(v) for v in bbox]
    w, h = x2 - x1, y2 - y1
    new_x1 = max(0, x1 - int(w * EXPAND_LEFT))
    new_y1 = max(0, y1 - int(h * EXPAND_TOP))
    new_x2 = min(img_shape[1], x2 + int(w * EXPAND_RIGHT))
    new_y2 = min(img_shape[0], y2 + int(h * EXPAND_BOTTOM))
    return [new_x1, new_y1, new_x2, new_y2]


def _resize_crop_with_letterbox(crop):
    h, w = crop.shape[:2]
    longest = max(h, w)
    if longest < CROP_MIN_SIZE:
        target = CROP_MIN_SIZE
    else:
        target = CROP_TARGET_SIZE
    scale = target / longest
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    resized = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    canvas = np.zeros((target, target, 3), dtype=np.uint8)
    x_off = (target - new_w) // 2
    y_off = (target - new_h) // 2
    canvas[y_off:y_off + new_h, x_off:x_off + new_w] = resized
    return canvas, new_w, new_h, scale


# ====== PER-RIDER MODEL INFERENCE ======

def _infer_on_rider_crop(crop, person_id, save_debug=True):
    """Run helmet model on a rider crop.
    
    Returns:
        (state, confidence, debug_info)
    """
    inference_debug = {
        'rider_id': person_id,
        'crop_original_shape': list(crop.shape[:2]),
        'model_decision': None,
        'model_confidence': None,
        'source': None,
    }

    service = get_helmet_service()
    if not service.is_available():
        inference_debug['source'] = 'model_unavailable'
        return HELMET_STATE_UNKNOWN, 0.0, inference_debug

    crop_for_model, new_w, new_h, scale = _resize_crop_with_letterbox(crop)
    inference_debug['crop_resized_shape'] = [new_h, new_w]
    inference_debug['crop_letterbox_shape'] = list(crop_for_model.shape[:2])
    inference_debug['scale_factor'] = round(scale, 4)

    # Check minimum resolution
    if new_w < 20 or new_h < 20:
        inference_debug['source'] = 'crop_too_small'
        inference_debug['reason'] = f'Crop too small: {new_w}x{new_h}'
        return HELMET_STATE_UNKNOWN, 0.0, inference_debug

    try:
        detections = service.detect(crop_for_model)
        inference_debug['raw_detections'] = [
            {'class': d['label'], 'class_id': d['class_id'],
             'confidence': round(d['confidence'], 3), 'bbox': [round(v, 1) for v in d['bbox']]}
            for d in detections
        ]
        inference_debug['detection_count'] = len(detections)

        if not detections:
            inference_debug['source'] = 'no_detections'
            return HELMET_STATE_UNKNOWN, 0.0, inference_debug

        # Pick highest-confidence detection
        best = max(detections, key=lambda d: d['confidence'])
        model_class = best['class_id']
        model_conf = best['confidence']
        inference_debug['best_detection'] = {
            'class': best['label'],
            'class_id': model_class,
            'confidence': round(model_conf, 3),
        }

        if model_class == 0:
            inference_debug['source'] = 'model_detected_helmet'
            return HELMET_STATE_PRESENT, model_conf, inference_debug

        if model_class == 1:
            if model_conf >= NO_HELMET_THRESHOLD:
                inference_debug['source'] = 'model_no_helmet_confident'
                return HELMET_STATE_ABSENT, model_conf, inference_debug
            else:
                inference_debug['source'] = 'model_no_helmet_low_conf'
                inference_debug['reason'] = f'Confidence {model_conf:.3f} < threshold {NO_HELMET_THRESHOLD}'
                return HELMET_STATE_UNKNOWN, model_conf, inference_debug

        inference_debug['source'] = 'unknown_class'
        inference_debug['reason'] = f'Unexpected class_id: {model_class}'
        return HELMET_STATE_UNKNOWN, model_conf, inference_debug

    except Exception as e:
        logger.error(f"Helmet inference error for {person_id}: {e}")
        inference_debug['source'] = 'inference_crash'
        inference_debug['reason'] = str(e)
        return HELMET_STATE_UNKNOWN, 0.0, inference_debug


# ====== HSV EMERGENCY FALLBACK ======

def _hsv_helmet_detect(image, person_bbox):
    """HSV-based helmet detection — emergency fallback only.
    
    Confidence is capped at 0.55. Never produces NO_HELMET alone.
    Returns:
        (state, confidence)
    """
    x1, y1, x2, y2 = [int(v) for v in person_bbox]
    person_h = y2 - y1
    person_w = x2 - x1

    if person_h < 20 or person_w < 10:
        return HELMET_STATE_UNKNOWN, 0.0

    head_y2 = y1 + int(person_h * 0.25)
    head_region = image[y1:head_y2, x1:x2]

    if head_region.size == 0:
        return HELMET_STATE_UNKNOWN, 0.0

    h, w = head_region.shape[:2]
    total_pixels = h * w
    if total_pixels < 50:
        return HELMET_STATE_UNKNOWN, 0.0

    hsv = cv2.cvtColor(head_region, cv2.COLOR_BGR2HSV)

    gray_head = cv2.cvtColor(head_region, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray_head, (5, 5), 0)
    edge_kernel = np.ones((3, 3), np.uint8)
    edges = cv2.Canny(blurred, 40, 120)
    edges = cv2.dilate(edges, edge_kernel, iterations=1)
    edge_density = cv2.countNonZero(edges) / total_pixels
    is_low_edge = edge_density < 0.25

    kernel = np.ones((5, 5), np.uint8)
    max_blob_ratio = 0.0

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

        if blob_ratio > max_blob_ratio:
            max_blob_ratio = blob_ratio

    # Cap confidence at 0.55 per v5 rule
    if is_low_edge:
        if max_blob_ratio > 0.12:
            return HELMET_STATE_PRESENT, min(max_blob_ratio * 1.2, 0.55)
        return HELMET_STATE_UNKNOWN, max(0.30, min(max_blob_ratio, 0.55))

    return HELMET_STATE_UNKNOWN, min(0.55, max(0.30, 1.0 - edge_density))


# ====== MAIN HELMET VIOLATION CHECK (v5) ======

def _make_violation(person, mc, confidence, helmet_state, severity, reason,
                    violation_type='NO_HELMET', needs_review=False):
    return {
        'violation_type': violation_type,
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
        'human_review_status': 'manual_verification_required' if needs_review else 'pending',
        'needs_review': needs_review,
    }


def _save_debug_crops(all_debug_entries, original_image):
    """Save rider crops to DEBUG_DIR and write helmet_inference_debug.json."""
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    session_dir = os.path.join(DEBUG_DIR, f'session_{timestamp}')
    os.makedirs(session_dir, exist_ok=True)

    for entry in all_debug_entries:
        rider_id = entry.get('rider_id', 'unknown')
        crop = entry.get('_crop_image')
        if crop is not None:
            crop_path = os.path.join(session_dir, f'{rider_id}_crop.jpg')
            cv2.imwrite(crop_path, crop)
            entry['crop_saved_path'] = crop_path
        entry.pop('_crop_image', None)

    json_path = os.path.join(session_dir, 'helmet_inference_debug.json')
    with open(json_path, 'w') as f:
        json.dump(all_debug_entries, f, indent=2)

    logger.info(f"Helmet debug: {len(all_debug_entries)} crops → {session_dir}")
    return session_dir


def check_helmet_violation(detections, image):
    """v5 crop-based helmet violation check.
    
    Pipeline:
      1. Associate persons to motorcycles (riders)
      2. For each rider, crop expanded bbox from ORIGINAL image
      3. Resize crop to 640x640 and run helmet_yolov8n.pt
      4. Determine state from model output
      5. HSV only as emergency fallback
      6. NO_HELMET only if model_class==WITHOUT_HELMET AND confidence >= 0.55
    
    Returns:
        list of violation dicts
    """
    persons = [d for d in detections if d['class_id'] == config.PERSON_CLASS_ID and d.get('confidence', 0) >= 0.25]
    motorcycles = [d for d in detections if d['class_id'] == config.MOTORCYCLE_CLASS_ID]

    if not persons or not motorcycles:
        return []

    img_shape = image.shape[:2] if image is not None else (None, None)
    associations = associate_riders(persons, motorcycles, img_shape)

    service = get_helmet_service()
    model_available = service.is_available()

    violations = []
    debug_entries = []
    any_model_inference = False

    for assoc in associations:
        mc = assoc['motorcycle']
        for person in assoc['riders']:
            person_bbox = person['bbox']
            person_id = person.get('instance_id', 'unknown')

            # Head area filter: skip riders whose head region is too small
            pw = person_bbox[2] - person_bbox[0]
            ph = person_bbox[3] - person_bbox[1]
            head_area = pw * ph * HEAD_AREA_RATIO
            if head_area < MIN_HEAD_AREA:
                debug_entries.append({
                    'rider_id': person_id,
                    'source': 'head_too_small',
                    'person_bbox': [round(v, 1) for v in person_bbox],
                    'head_area_px': round(head_area, 1),
                    'min_head_area': MIN_HEAD_AREA,
                })
                continue

            # Step 1: Crop from ORIGINAL image with expansion
            expanded = _expand_bbox(person_bbox, image.shape[:2])
            crop = image[expanded[1]:expanded[3], expanded[0]:expanded[2]]

            if crop.size == 0 or crop.shape[0] < 5 or crop.shape[1] < 5:
                debug_entries.append({
                    'rider_id': person_id,
                    'source': 'crop_invalid',
                    'crop_original_shape': [0, 0],
                    'model_decision': None,
                    'model_confidence': None,
                })
                # HSV emergency fallback
                hsv_state, hsv_conf = _hsv_helmet_detect(image, person_bbox)
                violations.append(_make_violation(
                    person, mc, hsv_conf, hsv_state,
                    config.RISK_SCORES.get('HELMET_ASSESSMENT_UNCERTAIN', 15),
                    'Crop invalid — HSV fallback. Manual review required.',
                    violation_type='HELMET_ASSESSMENT_UNCERTAIN',
                    needs_review=True,
                ))
                continue

            # Step 2: Run model on rider crop
            state, conf, dbg = _infer_on_rider_crop(crop, person_id)
            dbg['_crop_image'] = crop
            dbg['expanded_bbox'] = expanded
            dbg['person_bbox_original'] = [round(v, 1) for v in person_bbox]
            debug_entries.append(dbg)

            if dbg['source'] in ('model_detected_helmet', 'model_no_helmet_confident',
                                  'model_no_helmet_low_conf', 'no_detections'):
                any_model_inference = True

            # Step 3: Determine violation
            if state == HELMET_STATE_PRESENT:
                continue

            elif state == HELMET_STATE_ABSENT:
                severity = config.RISK_SCORES.get('NO_HELMET', 30)
                violations.append(_make_violation(
                    person, mc, conf, HELMET_STATE_ABSENT, severity,
                    f'Crop-based helmet detection: {person_id} classified as WITHOUT_HELMET (conf={conf:.3f}).',
                    violation_type='NO_HELMET',
                ))

            else:
                # HELMET_UNKNOWN — try HSV emergency fallback if model failed entirely
                if dbg.get('source') in ('model_unavailable', 'inference_crash', 'crop_too_small'):
                    hsv_state, hsv_conf = _hsv_helmet_detect(image, person_bbox)
                    if hsv_state == HELMET_STATE_PRESENT:
                        continue
                    violations.append(_make_violation(
                        person, mc, hsv_conf, HELMET_STATE_UNKNOWN,
                        config.RISK_SCORES.get('HELMET_ASSESSMENT_UNCERTAIN', 15),
                        f'Model unavailable/failed — HSV fallback. Manual review required.',
                        violation_type='HELMET_ASSESSMENT_UNCERTAIN',
                        needs_review=True,
                    ))
                else:
                    # Model ran but returned no helmet / low confidence
                    violations.append(_make_violation(
                        person, mc, conf, HELMET_STATE_UNKNOWN,
                        config.RISK_SCORES.get('HELMET_ASSESSMENT_UNCERTAIN', 15),
                        f'{person_id}: model returned {dbg.get("source", "unknown")} '
                        f'(conf={conf:.3f}). Manual review required.',
                        violation_type='HELMET_ASSESSMENT_UNCERTAIN',
                        needs_review=True,
                    ))

    # Save debug crops and inference JSON
    if debug_entries:
        _save_debug_crops(debug_entries, image)

    # Log diagnostics
    logger.info(
        f"Helmet v5: model={'available' if model_available else 'unavailable'}, "
        f"riders={sum(len(a['riders']) for a in associations)}, "
        f"model_inference={'yes' if any_model_inference else 'none'}, "
        f"violations={len(violations)}"
    )

    return violations
