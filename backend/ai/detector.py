import cv2
import numpy as np
from ultralytics import YOLO
import config


class ObjectDetector:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.model = None
        return cls._instance

    def load_model(self):
        if self.model is None:
            self.model = YOLO(config.YOLO_MODEL_NAME)
        return self.model

    def detect(self, image):
        model = self.load_model()
        results = model(image, conf=config.CONFIDENCE_THRESHOLD, agnostic_nms=getattr(config, 'AGNOSTIC_NMS', True))[0]
        detections = []
        if results.boxes is not None:
            boxes = results.boxes.xyxy.cpu().numpy()
            confs = results.boxes.conf.cpu().numpy()
            classes = results.boxes.cls.cpu().numpy().astype(int)
            for box, conf, cls_id in zip(boxes, confs, classes):
                label = config.CLASS_NAMES.get(cls_id, f'class_{cls_id}')
                detections.append({
                    'bbox': [float(x) for x in box],
                    'confidence': float(conf),
                    'class_id': int(cls_id),
                    'label': label,
                })
        return detections

    def filter_vehicles(self, detections):
        vehicles = []
        for det in detections:
            if det['class_id'] in config.VEHICLE_CLASSES:
                det['vehicle_type'] = config.VEHICLE_CLASSES[det['class_id']]
                vehicles.append(det)
        return vehicles

    def detect_vehicles(self, image):
        all_detections = self.detect(image)
        return self.filter_vehicles(all_detections)

    def filter_persons(self, detections):
        return [d for d in detections if d['class_id'] == config.PERSON_CLASS_ID]

    def filter_motorcycles(self, detections):
        return [d for d in detections if d['class_id'] == config.MOTORCYCLE_CLASS_ID]

    def detect_persons(self, image):
        return self.filter_persons(self.detect(image))

    def detect_motorcycles(self, image):
        return self.filter_motorcycles(self.detect(image))
