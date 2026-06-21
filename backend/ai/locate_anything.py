"""
Zero-shot object detector for TRINETRA AI.

Fallback chain:
  1. HF Inference API (google/owlvit-base-patch32) — fastest, needs HF_TOKEN
  2. YOLOv8 — always works, limited COCO classes
  3. Local OwlViT (transformers) — fully offline after model download
  4. Gradio API (LocateAnything HF spaces) — slow/unreliable, last

Detection targets:
  motorcycle, car, person, license plate, helmet, bus, truck, auto rickshaw
"""

import os, io, json, base64, time, logging, shutil
from typing import Optional

import cv2
import numpy as np
import requests

import config

logger = logging.getLogger(__name__)

# OwlViT via HF Inference API
OWLVIT_INFERENCE_URL = "https://api-inference.huggingface.co/models/google/owlvit-base-patch32"

# Multiple HF spaces for Gradio fallback
LOCATE_ANYTHING_SPACES = [
    "nvidia/LocateAnything",
    "ByteDance/LocateAnything",
]

# Default detection categories (expanded for better zero-shot coverage)
DEFAULT_CATEGORIES = "motorcycle, car, person, license plate, helmet, bus, truck, auto rickshaw, three wheeler, bicycle, traffic light"

# COCO class mapping for YOLO fallback
COCO_CLASSES = {
    0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle',
    5: 'bus', 7: 'truck',
}

ENGINE_YOLO = 'yolo'
ENGINE_HF_INFERENCE = 'locateanything'
ENGINE_OWLVIT_LOCAL = 'owlvit_local'
ENGINE_GRADIO = 'locateanything_gradio'

ENGINE_LABELS = {
    ENGINE_YOLO: 'YOLOv8 (COCO — fast, limited classes)',
    ENGINE_HF_INFERENCE: 'OwlViT via HF Inference API (zero-shot — needs HF token)',
    ENGINE_OWLVIT_LOCAL: 'OwlViT Local (zero-shot — heavy, needs model download)',
    ENGINE_GRADIO: 'LocateAnything Gradio (zero-shot — unreliable GPU)',
}


def check_owlvit_compatibility() -> dict:
    """Check if local OwlViT can run and estimate performance."""
    result = {
        'transformers_installed': False,
        'torch_installed': False,
        'cuda_available': False,
        'device': 'cpu',
        'estimated_ram_mb': 0,
        'can_run': False,
        'gpu_name': '',
        'download_size_mb': 0,
        'message': '',
    }
    try:
        import torch
        result['torch_installed'] = True
        result['cuda_available'] = torch.cuda.is_available()
        if result['cuda_available']:
            result['device'] = 'cuda'
            result['gpu_name'] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else ''
            try:
                total_mem = torch.cuda.get_device_properties(0).total_mem
                result['estimated_ram_mb'] = total_mem // (1024 * 1024)
            except Exception:
                result['estimated_ram_mb'] = 4096  # guess
        else:
            import psutil
            result['estimated_ram_mb'] = psutil.virtual_memory().total // (1024 * 1024)
    except ImportError:
        pass

    try:
        import transformers
        result['transformers_installed'] = True
    except ImportError:
        pass

    has_torch = result['torch_installed']
    has_transformers = result['transformers_installed']

    if has_torch and has_transformers:
        if result['cuda_available']:
            if result['estimated_ram_mb'] >= 2048:
                result['can_run'] = True
                result['message'] = (
                    f"GPU ({result['gpu_name']}) with {result['estimated_ram_mb']}MB VRAM available. "
                    "OwlViT will run with excellent performance."
                )
            else:
                result['can_run'] = True
                result['message'] = (
                    f"GPU ({result['gpu_name']}) with limited VRAM ({result['estimated_ram_mb']}MB). "
                    "OwlViT may be slow."
                )
        else:
            result['can_run'] = True
            result['message'] = (
                f"CPU with {result['estimated_ram_mb']}MB RAM. OwlViT will run but may be slow "
                "(5-15s per image)."
            )
    elif has_torch and not has_transformers:
        result['message'] = 'transformers library missing. Install with: pip install transformers'
    elif not has_torch:
        result['message'] = 'PyTorch not installed. Install with: pip install torch'
    else:
        result['message'] = 'Missing dependencies. Install: pip install torch transformers'

    # Model download size estimate (owlvit-base-patch32)
    result['download_size_mb'] = 380

    return result


def download_owlvit_model(progress_callback=None) -> dict:
    """Download and cache the OwlViT model from HuggingFace."""
    from transformers import pipeline as hf_pipeline
    import torch

    result = {'success': False, 'message': '', 'model_path': '', 'model_size_mb': 0}
    cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'huggingface', 'hub')

    try:
        logger.info('Downloading OwlViT model (google/owlvit-base-patch32)...')
        if progress_callback:
            progress_callback(10, 'Downloading model...')

        # Pipeline download triggers model download
        pipe = hf_pipeline(
            'zero-shot-object-detection',
            model='google/owlvit-base-patch32',
            device=0 if torch.cuda.is_available() else -1,
        )

        if progress_callback:
            progress_callback(90, 'Model downloaded, caching...')

        # Estimate size
        total_size = 0
        model_dir = None
        if os.path.exists(cache_dir):
            for root, dirs, files in os.walk(cache_dir):
                if 'owlvit' in root.lower() or 'google' in root.lower():
                    for f in files:
                        fp = os.path.join(root, f)
                        if os.path.isfile(fp):
                            total_size += os.path.getsize(fp)
                    if model_dir is None:
                        model_dir = root

        result['success'] = True
        result['model_path'] = model_dir or ''
        result['model_size_mb'] = total_size // (1024 * 1024)
        result['message'] = (
            f"OwlViT model downloaded successfully ({result['model_size_mb']}MB). "
            "Ready for zero-shot detection."
        )
        logger.info(result['message'])

        # Cache the pipeline on the singleton
        from ai.locate_anything import LocateAnythingDetector
        det = LocateAnythingDetector()
        det._owl_pipeline = pipe

    except Exception as e:
        result['message'] = f'Failed to download OwlViT model: {e}'
        logger.error(result['message'])

    return result


class LocateAnythingDetector:
    """Zero-shot object detector with multiple fallback tiers."""

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
        self._gradio_failed = False
        self._owl_pipeline = None
        self._yolo_model = None
        self._active_mode = None
        self._hf_token = os.environ.get("HF_TOKEN", "")

    def set_hf_token(self, token: str):
        self._hf_token = token

    def get_available_engines(self) -> list:
        engines = []
        engines.append({'id': ENGINE_YOLO, 'label': ENGINE_LABELS[ENGINE_YOLO], 'available': True})

        hf_avail = bool(self._hf_token)
        engines.append({
            'id': ENGINE_HF_INFERENCE,
            'label': ENGINE_LABELS[ENGINE_HF_INFERENCE],
            'available': hf_avail,
            'needs_token': True,
            'token_set': hf_avail,
        })

        try:
            import transformers
            import torch
            owl_local_avail = True
        except ImportError:
            owl_local_avail = False
        engines.append({
            'id': ENGINE_OWLVIT_LOCAL,
            'label': ENGINE_LABELS[ENGINE_OWLVIT_LOCAL],
            'available': owl_local_avail,
            'needs_download': self._owl_pipeline is None,
        })

        engines.append({
            'id': ENGINE_GRADIO,
            'label': ENGINE_LABELS[ENGINE_GRADIO],
            'available': not self._gradio_failed,
        })

        return engines

    # ────────── Tier 1: HF Inference API (OwlViT) ──────────

    def _detect_hf_inference(self, image: np.ndarray, categories: str) -> list:
        """Use HuggingFace Inference API for zero-shot OwlViT detection."""
        token = self._hf_token
        if not token:
            return []

        try:
            _, img_encoded = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
            img_bytes = img_encoded.tobytes()

            labels = [c.strip() for c in categories.split(',')]

            resp = requests.post(
                OWLVIT_INFERENCE_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "inputs": base64.b64encode(img_bytes).decode('utf-8'),
                    "parameters": {"candidate_labels": labels},
                },
                timeout=30,
            )

            if resp.status_code != 200:
                logger.warning(f"HF Inference API returned {resp.status_code}: {resp.text[:200]}")
                return []

            results = resp.json()
            if not isinstance(results, list):
                logger.warning(f"HF Inference API unexpected response: {type(results)}")
                return []

            detections = []
            for r in results:
                box = r.get('box', {})
                if 'xmin' not in box:
                    continue
                detections.append({
                    'bbox': [box['xmin'], box['ymin'], box['xmax'], box['ymax']],
                    'confidence': r.get('score', 0.5),
                    'class_id': self._label_to_class_id(r.get('label', 'object')),
                    'label': r.get('label', 'object').lower(),
                })

            if detections:
                logger.info(f"HF Inference API: {len(detections)} detections")
                return detections
            return []

        except requests.exceptions.Timeout:
            logger.warning("HF Inference API: timed out")
            return []
        except Exception as e:
            logger.warning(f"HF Inference API: failed: {e}")
            return []

    # ────────── Tier 2: YOLOv8 fallback ──────────

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

    # ────────── Tier 3: Local OwlViT (transformers) ──────────

    def _init_owlvit(self):
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
        except ImportError:
            logger.debug("LocateAnything: transformers not installed")
            return False
        except Exception as e:
            logger.warning(f"LocateAnything: OwlViT init failed: {e}")
            return False

    def _detect_owlvit(self, image: np.ndarray, categories: str) -> list:
        if self._owl_pipeline is None:
            if not self._init_owlvit():
                return []

        try:
            img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            labels = [c.strip() for c in categories.split(',')]
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
            if detections:
                logger.info(f"OwlViT local: {len(detections)} detections")
            return detections
        except Exception as e:
            logger.warning(f"OwlViT local: {e}")
            return []

    # ────────── Tier 4: Gradio API (LocateAnything HF spaces) ──────────

    def _detect_gradio_client(self, image: np.ndarray, categories: str) -> list:
        """Use gradio_client library (more reliable than raw REST API)."""
        try:
            import gradio_client
            from gradio_client import file as gc_file
            HAS_GRADIO_CLIENT = True
        except ImportError:
            logger.debug("Gradio client: gradio_client not installed")
            return []

        try:
            _, img_buf = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
            img_bytes = img_buf.tobytes()

            for space in LOCATE_ANYTHING_SPACES:
                hf_space = f"https://huggingface.co/spaces/{space}"
                try:
                    client = gradio_client.Client(space, hf_token=True, timeout=60)

                    # Use the v2 API endpoint with the right parameters
                    result = client.predict(
                        "Image",                  # input_type
                        gc_file(img_bytes),       # image_file
                        None,                     # video_file
                        "Detection",              # task_type
                        categories,               # category
                        "fast",                   # model_mode
                        0.7,                      # temp
                        0.9,                      # top_p
                        10,                       # top_k
                        640,                      # short_size
                        None,                     # question_override
                        1,                        # max_video_frames
                        api_name="/v2/run_inference",
                    )

                    if result and isinstance(result, (list, tuple)) and len(result) > 2:
                        meta = result[2] if isinstance(result[2], dict) else {}
                        if isinstance(meta, dict) and meta.get('success') and 'detections' in meta:
                            dets = self._format_gradio_detections(meta['detections'], image.shape)
                            if dets:
                                self._active_mode = f'locateanything_api_{space.split("/")[-1]}'
                                logger.info(f"Gradio client {space}: {len(dets)} detections")
                                return dets

                except Exception as e:
                    logger.debug(f"Gradio client {space}: {e}")
                    continue

            return []

        except Exception as e:
            logger.debug(f"Gradio client failed: {e}")
            return []

    def _detect_gradio_rest(self, image: np.ndarray, categories: str) -> list:
        """Fallback REST API call if gradio_client fails."""
        if self._gradio_failed:
            return []

        try:
            _, img_encoded = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
            img_bytes = img_encoded.tobytes()

            for space in LOCATE_ANYTHING_SPACES:
                space_domain = f"https://{space.replace('/', '-')}.hf.space"
                try:
                    upload_resp = requests.post(
                        f"{space_domain}/gradio_api/upload",
                        files={"files": ("image.jpg", img_bytes, "image/jpeg")},
                        timeout=10,
                    )
                    if upload_resp.status_code != 200:
                        continue

                    file_path = upload_resp.json()[0]

                    payload = {
                        "input_type": "Image",
                        "image_file": {"path": file_path},
                        "video_file": None,
                        "task_type": "Detection",
                        "category": categories,
                        "model_mode": "fast",
                        "temp": 0.7,
                        "top_p": 0.9,
                        "top_k": 10,
                        "short_size": 640,
                        "question_override": None,
                        "max_video_frames": 1,
                    }

                    event_resp = requests.post(
                        f"{space_domain}/gradio_api/call/v2/run_inference",
                        json=payload,
                        timeout=20,
                    )
                    if event_resp.status_code != 200:
                        continue

                    event_id = event_resp.json().get('event_id')
                    if not event_id:
                        continue

                    for _ in range(10):
                        poll_resp = requests.get(
                            f"{space_domain}/gradio_api/call/run_inference/{event_id}",
                            timeout=8,
                        )
                        body = poll_resp.text
                        if 'event: complete' in body:
                            for line in body.split('\n'):
                                line = line.strip()
                                if line.startswith('data: '):
                                    data = json.loads(line[6:])
                                    meta = data[2] if len(data) > 2 else {}
                                    if isinstance(meta, dict) and meta.get('success') and 'detections' in meta:
                                        dets = self._format_gradio_detections(meta['detections'], image.shape)
                                        if dets:
                                            self._active_mode = f'locateanything_api_{space.split("/")[-1]}'
                                            logger.info(f"Gradio {space}: {len(dets)} detections")
                                            return dets
                                    else:
                                        err = meta.get('error', '') if isinstance(meta, dict) else ''
                                        logger.debug(f"Gradio {space}: inference error: {err}")
                                        break
                        elif 'event: error' in body:
                            logger.debug(f"Gradio {space}: event error")
                            break
                        time.sleep(1.0)
                except Exception:
                    continue

            self._gradio_failed = True
            return []

        except Exception as e:
            logger.warning(f"Gradio REST API: {e}")
            self._gradio_failed = True
            return []

    def _format_gradio_detections(self, raw_detections: dict, img_shape) -> list:
        detections = []
        if not isinstance(raw_detections, dict):
            return detections

        items = raw_detections.get('items') or raw_detections.get('detections', [])
        if not items and isinstance(raw_detections, list):
            items = raw_detections

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

    # ────────── Engine-specific detection ──────────

    def detect_with_engine(self, image: np.ndarray, engine: str,
                           categories: Optional[str] = None,
                           hf_token: Optional[str] = None) -> list:
        """Run detection with a specific engine."""
        cats = categories or DEFAULT_CATEGORIES

        if hf_token:
            self._hf_token = hf_token

        if engine == ENGINE_HF_INFERENCE:
            dets = self._detect_hf_inference(image, cats)
            self._active_mode = 'hf_inference_api_owlvit' if dets else f'{engine}_no_results'
            return dets

        elif engine == ENGINE_YOLO:
            dets = self._detect_yolo(image)
            self._active_mode = 'yolo' if dets else f'{engine}_no_results'
            return dets

        elif engine == ENGINE_OWLVIT_LOCAL:
            dets = self._detect_owlvit(image, cats)
            self._active_mode = 'owlvit_local' if dets else f'{engine}_no_results'
            return dets

        elif engine == ENGINE_GRADIO:
            self._gradio_failed = False
            dets = self._detect_gradio_client(image, cats)
            if dets:
                self._active_mode = 'locateanything_gradio_client'
                return dets
            dets = self._detect_gradio_rest(image, cats)
            if dets:
                self._active_mode = 'locateanything_gradio_rest'
                return dets
            self._active_mode = 'locateanything_gradio_no_results'
            return []

        else:
            logger.warning(f"Unknown engine: {engine}, falling back to auto")
            return self.detect(image, cats)

    # ────────── Public API ──────────

    def detect(self, image: np.ndarray, categories: Optional[str] = None) -> list:
        """Auto-detect with best available method."""
        cats = categories or DEFAULT_CATEGORIES

        dets = self._detect_hf_inference(image, cats)
        if dets:
            self._active_mode = 'hf_inference_api_owlvit'
            return dets

        dets = self._detect_yolo(image)
        if dets:
            self._active_mode = 'yolo'
            return dets

        dets = self._detect_owlvit(image, cats)
        if dets:
            self._active_mode = 'owlvit_local'
            return dets

        dets = self._detect_gradio_rest(image, cats)
        if dets:
            return dets

        self._active_mode = 'fallback_empty'
        return []

    def get_model_info(self) -> dict:
        return {
            'active_mode': self.get_active_mode(),
            'hf_inference_available': bool(self._hf_token),
            'owlvit_local_available': self._owl_pipeline is not None,
            'yolo_available': True,
            'gradio_available': not self._gradio_failed,
        }

    def get_active_mode(self) -> str:
        return self._active_mode or 'not_initialized'

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
