"""
LocateAnything-based detector for TRINETRA AI.

Uses NVIDIA's LocateAnything (GroundingDINO + SAM) via Gradio API
for zero-shot object detection with text prompts.

Fallback chain:
  1. LocateAnything Gradio API (multiple HF spaces)
  2. Local zero-shot model via transformers (OwlViT)
  3. YOLOv8n (ultralytics) — always works

Detection targets (text prompts):
  motorcycle, car, person, license plate, helmet, bus, truck
"""

import os, io, json, base64, time, logging
from typing import Optional

import cv2
import numpy as np

# Try Gradio client
try:
    from gradio_client import Client, handle_file
    HAS_GRADIO = True
except ImportError:
    HAS_GRADIO = False

# Try transformers (for local zero-shot fallback) — lazy import with timeout
HAS_TRANSFORMERS = False
_tried_transformers = False

# YOLO is always our base fallback
import config

logger = logging.getLogger(__name__)

# Multiple HF spaces to try (ordered by preference)
LOCATE_ANYTHING_SPACES = [
    "nvidia/LocateAnything",
    "ByteDance/LocateAnything",
]

HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Default detection categories (expanded for better zero-shot coverage)
DEFAULT_CATEGORIES = "motorcycle, car, person, license plate, helmet, bus, truck, auto rickshaw, three wheeler, bicycle, traffic light"

# COCO class mapping for YOLO fallback
COCO_CLASSES = {
    0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle',
    5: 'bus', 7: 'truck',
}


class LocateAnythingDetector:
    """Zero-shot object detector using LocateAnything API with fallbacks."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._gradio_clients = []
        self._gradio_permanent_fail = False
        self._owl_pipeline = None
        self._yolo_model = None
        self._active_mode = None

    # ---------- Tier 1: LocateAnything Gradio API ----------

    def _init_gradio(self):
        if not HAS_GRADIO or self._gradio_permanent_fail:
            return False

        for space_url in LOCATE_ANYTHING_SPACES:
            try:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(Client, space_url)
                    try:
                        client = future.result(timeout=60)
                        self._gradio_clients.append(client)
                        logger.info(f"LocateAnything: Gradio client initialized for {space_url}")
                        return True
                    except concurrent.futures.TimeoutError:
                        logger.warning(f"LocateAnything: Gradio client init timed out for {space_url} (60s)")
                        continue
            except Exception as e:
                logger.warning(f"LocateAnything: Gradio init failed for {space_url}: {e}")
                continue

        logger.warning("LocateAnything: all Gradio spaces failed to initialize")
        self._gradio_permanent_fail = True
        return False

    def _detect_gradio(self, image: np.ndarray, categories: str) -> list:
        if not self._gradio_clients:
            if not self._init_gradio():
                return []

        temp_path = None
        for space_idx, client in enumerate(self._gradio_clients):
            try:
                from tempfile import NamedTemporaryFile
                tmpf = NamedTemporaryFile(suffix='.jpg', delete=False)
                tmpf.close()
                temp_path = tmpf.name
                cv2.imwrite(temp_path, image)

                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        client.predict,
                        'Image',
                        handle_file(temp_path),
                        None,
                        'Detection',
                        categories or DEFAULT_CATEGORIES,
                        'hybrid',
                        0.7, 0.9, 20, None, None, 4,
                        api_name='/run_inference',
                    )
                    try:
                        result = future.result(timeout=120)
                    except concurrent.futures.TimeoutError:
                        logger.warning(f"LocateAnything: Gradio API timed out (120s) for space {space_idx}")
                        continue

                if result and len(result) >= 3:
                    meta = result[2]
                    if isinstance(meta, dict) and meta.get('success') and 'detections' in meta:
                        dets = self._format_gradio_detections(meta['detections'], image.shape)
                        if dets:
                            self._active_mode = f'locateanything_api_{LOCATE_ANYTHING_SPACES[space_idx].split("/")[-1]}'
                            return dets
                continue
            except Exception as e:
                logger.warning(f"LocateAnything: Gradio inference failed for space {space_idx}: {e}")
                continue
            finally:
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass

        return []

    def _format_gradio_detections(self, raw_detections: dict, img_shape) -> list:
        """Convert LocateAnything detection format to our standard format."""
        detections = []
        if not isinstance(raw_detections, dict):
            return detections

        items = raw_detections.get('items') or raw_detections.get('detections', [])
        if not items and isinstance(raw_detections, list):
            items = raw_detections

        h, w = img_shape[:2]

        for item in items:
            if isinstance(item, dict):
                label = item.get('label', item.get('category', 'object'))
                score = float(item.get('score', item.get('confidence', 0.5)))
                box = item.get('bbox', item.get('box', item.get('bbox_xyxy')))
                if box and len(box) >= 4:
                    x1, y1, x2, y2 = map(float, box[:4])
                    class_id = self._label_to_class_id(label)
                    detections.append({
                        'bbox': [x1, y1, x2, y2],
                        'confidence': score,
                        'class_id': class_id,
                        'label': label.lower(),
                    })
        return detections

    def _label_to_class_id(self, label: str) -> int:
        mapping = {
            'person': 0, 'bicycle': 1, 'car': 2, 'motorcycle': 3,
            'bus': 5, 'truck': 7, 'license plate': 99, 'helmet': 98,
            'auto rickshaw': 2, 'three wheeler': 2,
        }
        return mapping.get(label.lower().strip(), -1)

    # ---------- Tier 2: Local zero-shot model (OwlViT) ----------

    def _init_owlvit(self):
        global HAS_TRANSFORMERS, _tried_transformers
        if not HAS_TRANSFORMERS and not _tried_transformers:
            _tried_transformers = True
            try:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(__import__, 'transformers')
                    try:
                        future.result(timeout=30)
                        from transformers import pipeline
                        HAS_TRANSFORMERS = True
                        logger.info("LocateAnything: transformers loaded")
                    except concurrent.futures.TimeoutError:
                        logger.warning("LocateAnything: transformers import timed out (30s)")
                        HAS_TRANSFORMERS = False
            except Exception:
                HAS_TRANSFORMERS = False
        if not HAS_TRANSFORMERS:
            return False
        try:
            import torch
            from transformers import pipeline
            self._owl_pipeline = pipeline(
                'zero-shot-object-detection',
                model='google/owlvit-base-patch32',
                device=0 if torch.cuda.is_available() else -1,
            )
            logger.info("LocateAnything: OwlViT pipeline loaded")
            return True
        except Exception as e:
            logger.warning(f"LocateAnything: OwlViT init failed: {e}")
            return False

    def _detect_owlvit(self, image: np.ndarray, categories: str) -> list:
        if self._owl_pipeline is None:
            if not self._init_owlvit():
                return []

        try:
            img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            labels = [c.strip() for c in (categories or DEFAULT_CATEGORIES).split(',')]
            results = self._owl_pipeline(img_rgb, candidate_labels=labels)

            detections = []
            for r in results:
                box = r['box']
                detections.append({
                    'bbox': [box['xmin'], box['ymin'], box['xmax'], box['ymax']],
                    'confidence': r['score'],
                    'class_id': self._label_to_class_id(r['label']),
                    'label': r['label'].lower(),
                })
            return detections
        except Exception as e:
            logger.warning(f"LocateAnything: OwlViT inference failed: {e}")
            return []

    # ---------- Tier 3: YOLOv8 fallback ----------

    def _init_yolo(self):
        try:
            from ultralytics import YOLO
            self._yolo_model = YOLO(config.YOLO_MODEL_NAME)
            logger.info("LocateAnything: YOLO fallback loaded")
            return True
        except Exception as e:
            logger.error(f"LocateAnything: YOLO init failed: {e}")
            return False

    def _detect_yolo(self, image: np.ndarray) -> list:
        if self._yolo_model is None:
            if not self._init_yolo():
                return []

        try:
            results = self._yolo_model(image, conf=config.CONFIDENCE_THRESHOLD, agnostic_nms=config.AGNOSTIC_NMS)[0]
            detections = []
            if results.boxes is not None:
                boxes = results.boxes.xyxy.cpu().numpy()
                confs = results.boxes.conf.cpu().numpy()
                classes = results.boxes.cls.cpu().numpy().astype(int)
                for box, conf, cls_id in zip(boxes, confs, classes):
                    detections.append({
                        'bbox': [float(x) for x in box],
                        'confidence': float(conf),
                        'class_id': int(cls_id),
                        'label': config.CLASS_NAMES.get(int(cls_id), f'class_{cls_id}'),
                    })
            return detections
        except Exception as e:
            logger.error(f"LocateAnything: YOLO inference failed: {e}")
            return []

    # ---------- Public API ----------

    def detect(self, image: np.ndarray, categories: Optional[str] = None) -> list:
        """Detect objects in image using best available method.

        Fallback chain:
          1. LocateAnything Gradio API (multiple HF spaces, long timeout)
          2. Local OwlViT (transformers)
          3. YOLOv8

        Args:
            image: BGR numpy array (OpenCV format)
            categories: Comma-separated text prompts

        Returns:
            List of dicts with keys: bbox, confidence, class_id, label
        """
        cats = categories or DEFAULT_CATEGORIES

        # Tier 1: LocateAnything API (retry once on first call)
        if HAS_GRADIO and not self._gradio_permanent_fail:
            dets = self._detect_gradio(image, cats)
            if dets:
                return dets
            # Don't permanently give up — next request may succeed
            if self._gradio_permanent_fail:
                logger.info("LocateAnything: Gradio permanently unavailable, skipping in future")

        # Tier 2: Local zero-shot model
        if HAS_TRANSFORMERS or not _tried_transformers:
            dets = self._detect_owlvit(image, cats)
            if dets:
                self._active_mode = 'owlvit_local'
                return dets

        # Tier 3: YOLO fallback
        dets = self._detect_yolo(image)
        self._active_mode = 'yolo_fallback'
        return dets

    def get_model_info(self) -> dict:
        """Return diagnostic info about the active detection model."""
        return {
            'active_mode': self.get_active_mode(),
            'gradio_available': HAS_GRADIO and not self._gradio_permanent_fail,
            'owlvit_available': HAS_TRANSFORMERS,
            'yolo_available': True,
            'gradio_clients': len(self._gradio_clients),
        }

    def filter_vehicles(self, detections: list) -> list:
        vehicles = []
        for det in detections:
            cls_id = det.get('class_id', -1)
            label = det.get('label', '')
            if cls_id in config.VEHICLE_CLASSES:
                det['vehicle_type'] = config.VEHICLE_CLASSES.get(cls_id, 'vehicle')
                vehicles.append(det)
            elif label in ('car', 'motorcycle', 'bus', 'truck', 'vehicle', 'auto rickshaw', 'three wheeler'):
                det['vehicle_type'] = label
                vehicles.append(det)
        return vehicles

    def filter_persons(self, detections: list) -> list:
        return [d for d in detections
                if d.get('class_id') == 0 or d.get('label') == 'person']

    def filter_motorcycles(self, detections: list) -> list:
        return [d for d in detections
                if d.get('class_id') == 3 or d.get('label') == 'motorcycle']

    def detect_vehicles(self, image: np.ndarray) -> list:
        return self.filter_vehicles(self.detect(image))

    def detect_persons(self, image: np.ndarray) -> list:
        return self.filter_persons(self.detect(image))

    def detect_motorcycles(self, image: np.ndarray) -> list:
        return self.filter_motorcycles(self.detect(image))

    def get_active_mode(self) -> str:
        return self._active_mode or 'not_initialized'
