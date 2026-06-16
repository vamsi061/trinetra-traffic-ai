import cv2
import numpy as np
import re
import config
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False


class LicensePlateReader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.reader = None
        return cls._instance

    def load_reader(self):
        if self.reader is None and EASYOCR_AVAILABLE:
            self.reader = easyocr.Reader(['en'], gpu=False)
        return self.reader

    def extract_plate_region(self, image, vehicle_bbox):
        x1, y1, x2, y2 = [int(v) for v in vehicle_bbox]
        h = y2 - y1
        w = x2 - x1
        plate_y1 = y1 + int(h * 0.55)
        plate_y2 = y2
        plate_x1 = x1 + int(w * 0.1)
        plate_x2 = x2 - int(w * 0.1)
        plate_y1 = max(0, plate_y1)
        plate_y2 = min(image.shape[0], plate_y2)
        plate_x1 = max(0, plate_x1)
        plate_x2 = min(image.shape[1], plate_x2)
        if plate_y2 <= plate_y1 or plate_x2 <= plate_x1:
            return None
        region = image[plate_y1:plate_y2, plate_x1:plate_x2]
        return region

    def find_plate_contours(self, region):
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        edged = cv2.Canny(gray, 30, 200)
        contours, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
        plate_candidates = []
        for cnt in contours:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.018 * peri, True)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = w / float(h)
                if 1.5 <= aspect_ratio <= 6.0 and w > 30 and h > 10:
                    plate_candidates.append((x, y, w, h))
        return plate_candidates

    def validate_plate_format(self, text):
        patterns = [
            r'^[A-Z]{2}\d{1,2}[A-Z]{1,2}\d{1,4}$',
            r'^[A-Z]{2}\d{2}[A-Z]{2}\d{4}$',
            r'^\d{1,4}[A-Z]{1,3}\d{1,4}$',
            r'^[A-Z]{1,3}\d{1,4}[A-Z]{1,2}$',
        ]
        return any(re.match(p, text) for p in patterns)

    def read_plate(self, image, vehicle_bbox):
        region = self.extract_plate_region(image, vehicle_bbox)
        if region is None or region.size == 0:
            return '', 0.0
        if EASYOCR_AVAILABLE:
            reader = self.load_reader()
            if reader:
                results = reader.readtext(region)
                if results:
                    texts = []
                    confs = []
                    for bbox, text, conf in results:
                        if conf >= config.OCR_CONFIDENCE_THRESHOLD:
                            cleaned = re.sub(r'[^A-Za-z0-9]', '', text).upper()
                            if len(cleaned) >= 4 and self.validate_plate_format(cleaned):
                                texts.append(cleaned)
                                confs.append(conf)
                    if texts:
                        best_idx = int(np.argmax(confs))
                        return texts[best_idx], float(confs[best_idx])
        plate_candidates = self.find_plate_contours(region)
        if plate_candidates:
            for x, y, w, h in plate_candidates:
                plate_roi = region[y:y+h, x:x+w]
                if plate_roi.size > 0:
                    gray = cv2.cvtColor(plate_roi, cv2.COLOR_BGR2GRAY)
                    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    if EASYOCR_AVAILABLE and self.reader:
                        results = self.reader.readtext(thresh)
                        if results:
                            text = re.sub(r'[^A-Za-z0-9]', '', results[0][1]).upper()
                            if len(text) >= 4 and self.validate_plate_format(text):
                                return text, float(results[0][2])
        return '', 0.0
