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
        img_h, img_w = image.shape[:2]

        plate_y1 = y1 + int(h * 0.45)
        plate_y2 = y2
        plate_x1 = x1 + int(w * 0.05)
        plate_x2 = x2 - int(w * 0.05)

        plate_y1 = max(0, plate_y1)
        plate_y2 = min(img_h, plate_y2)
        plate_x1 = max(0, plate_x1)
        plate_x2 = min(img_w, plate_x2)
        if plate_y2 <= plate_y1 or plate_x2 <= plate_x1:
            return None
        return image[plate_y1:plate_y2, plate_x1:plate_x2]

    def extract_full_vehicle_region(self, image, vehicle_bbox):
        x1, y1, x2, y2 = [int(v) for v in vehicle_bbox]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(image.shape[1], x2)
        y2 = min(image.shape[0], y2)
        if y2 <= y1 or x2 <= x1:
            return None
        return image[y1:y2, x1:x2]

    def validate_plate_format(self, text):
        if len(text) < 4:
            return False
        patterns = [
            r'^[A-Z]{2}\d{1,2}[A-Z]{1,2}\d{1,4}$',
            r'^[A-Z]{2}\d{2}[A-Z]{2}\d{4}$',
            r'^\d{1,4}[A-Z]{1,3}\d{1,4}$',
            r'^[A-Z]{1,3}\d{1,4}[A-Z]{1,2}$',
            r'^\d{2,3}[A-Z]{2}\d{4}$',
            r'^[A-Z]{2,3}\d{4,6}$',
        ]
        if any(re.match(p, text) for p in patterns):
            return True
        has_letter = any(c.isalpha() for c in text)
        has_digit = any(c.isdigit() for c in text)
        return has_letter and has_digit and len(text) >= 4

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

    def _combine_fragments(self, results):
        if not results:
            return '', 0.0

        filtered = []
        for bbox, text, conf in results:
            if conf < config.OCR_CONFIDENCE_THRESHOLD:
                continue
            cleaned = re.sub(r'[^A-Za-z0-9]', '', text).upper()
            if len(cleaned) < 2:
                continue
            xs = [p[0] for p in bbox]
            cx = sum(xs) / len(xs)
            filtered.append({'text': cleaned, 'conf': conf, 'cx': cx})

        if not filtered:
            return '', 0.0

        filtered.sort(key=lambda x: x['cx'])

        # Combine all fragments sorted left-to-right
        combined = ''.join(g['text'] for g in filtered)
        avg_conf = sum(g['conf'] for g in filtered) / len(filtered)
        if self.validate_plate_format(combined):
            return combined, avg_conf

        # Try subsets (drop leftmost or rightmost outlier)
        for drop_end in ('left', 'right'):
            subset = filtered[1:] if drop_end == 'left' else filtered[:-1]
            if len(subset) < 2:
                continue
            combined = ''.join(g['text'] for g in subset)
            avg_conf = sum(g['conf'] for g in subset) / len(subset)
            if self.validate_plate_format(combined):
                return combined, avg_conf

        # Last resort: best individual fragment
        best_text, best_conf = '', 0.0
        for g in filtered:
            if self.validate_plate_format(g['text']) and g['conf'] > best_conf:
                best_text, best_conf = g['text'], g['conf']

        return best_text, best_conf

    def _run_easyocr(self, image):
        if not EASYOCR_AVAILABLE:
            return '', 0.0
        self.load_reader()
        if not self.reader:
            return '', 0.0
        results = self.reader.readtext(image)
        return self._combine_fragments(results)

    def _upscale_region(self, region, target_height=200):
        h, w = region.shape[:2]
        if h < target_height:
            scale = target_height / h
            new_w = int(w * scale)
            return cv2.resize(region, (new_w, target_height), interpolation=cv2.INTER_CUBIC)
        return region

    def read_plate(self, image, vehicle_bbox):
        full = self.extract_full_vehicle_region(image, vehicle_bbox)
        best_text, best_conf = '', 0.0

        if full is not None and full.size > 0 and full.shape[0] > 20 and full.shape[1] > 20:
            # Upscale for better OCR
            upscaled = self._upscale_region(full)
            gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)

            # Try multiple preprocessing methods on the full region
            methods = [
                ('raw_bgr', upscaled),
                ('grayscale', gray),
                ('clahe', cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)),
                ('otsu', cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]),
                ('adaptive', cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)),
                ('bilateral', cv2.bilateralFilter(gray, 9, 75, 75)),
            ]

            for name, proc in methods:
                text, conf = self._run_easyocr(proc)
                if text and conf > best_conf:
                    best_text, best_conf = text, conf
                # Prefer longer text (more complete plate)
                if text and len(text) >= len(best_text) and conf >= best_conf - 0.1:
                    best_text, best_conf = text, max(best_conf, conf)
                if best_text and len(best_text) >= 8 and best_conf >= 0.4:
                    return best_text, best_conf

        # Fallback: lower region for cars
        if best_text and best_conf >= 0.3:
            return best_text, best_conf

        region = self.extract_plate_region(image, vehicle_bbox)
        if region is not None and region.size > 0:
            text, conf = self._run_easyocr(region)
            if text and conf > best_conf:
                best_text, best_conf = text, conf

        # Contour fallback
        if full is not None and full.size > 0 and not best_text:
            candidates = self.find_plate_contours(full)
            if candidates:
                for x, y, w, h in candidates:
                    plate_roi = full[y:y+h, x:x+w]
                    if plate_roi.size > 0:
                        up = self._upscale_region(plate_roi)
                        gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)
                        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                        text, conf = self._run_easyocr(thresh)
                        if text and conf > best_conf:
                            best_text, best_conf = text, conf

        return best_text, best_conf
