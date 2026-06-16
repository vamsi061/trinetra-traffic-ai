import streamlit as st
import cv2
import numpy as np
import os
from datetime import datetime
from PIL import Image

from utils.image_processing import enhance_image
from ai.detector import ObjectDetector
from ai.helmet_detector import check_helmet_violation
from ai.triple_riding import check_triple_riding
from ai.ocr import LicensePlateReader
from ai.evidence_generator import generate_evidence
from database.db import insert_violation
from database.models import ViolationRecord
import config


def save_uploaded_image(uploaded_file):
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'upload_{timestamp}_{uploaded_file.name}'
    filepath = os.path.join(config.UPLOAD_DIR, filename)
    with open(filepath, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    return filepath, filename


def show():
    st.title("Traffic Image Analysis")
    st.markdown("Upload a traffic image for AI-powered violation detection")

    uploaded_file = st.file_uploader(
        "Choose a traffic image...",
        type=['jpg', 'jpeg', 'png', 'bmp', 'webp']
    )

    if uploaded_file is not None:
        file_bytes = np.frombuffer(uploaded_file.read(), np.uint8)
        original = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if original is None:
            st.error("Failed to decode image. Please upload a valid image file.")
            return

        original_rgb = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Original Image")
            st.image(original_rgb, use_container_width=True)

        with st.spinner("Processing image..."):
            saved_path, saved_name = save_uploaded_image(uploaded_file)
            processed = enhance_image(original)
            processed_rgb = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)

            with col2:
                st.subheader("Enhanced Image")
                st.image(processed_rgb, use_container_width=True)

            detector = ObjectDetector()
            detections = detector.detect(processed)

            if not detections:
                st.warning("No objects detected in the image. Try a different image.")
                return

            st.subheader("Detection Results")
            st.json([{
                'label': d['label'],
                'confidence': round(d['confidence'], 3),
                'bbox': [round(v, 1) for v in d['bbox']]
            } for d in detections])

            violations = []
            helmet_violations = check_helmet_violation(detections, processed)
            violations.extend(helmet_violations)

            triple_violations = check_triple_riding(detections)
            violations.extend(triple_violations)

            plate_text = ''
            plate_conf = 0.0
            vehicles = detector.detect_vehicles(processed)
            if vehicles:
                reader = LicensePlateReader()
                biggest_vehicle = max(vehicles, key=lambda v: (
                    (v['bbox'][2] - v['bbox'][0]) *
                    (v['bbox'][3] - v['bbox'][1])
                ))
                plate_text, plate_conf = reader.read_plate(processed, biggest_vehicle['bbox'])

            evidence_path = generate_evidence(processed, detections, violations, (plate_text, plate_conf))

            for v in violations:
                vehicle_type = ''
                for det in detections:
                    if det['class_id'] in config.VEHICLE_CLASSES:
                        vehicle_type = config.VEHICLE_CLASSES[det['class_id']]
                        break
                record = ViolationRecord(
                    vehicle_number=plate_text,
                    vehicle_type=vehicle_type,
                    violation_type=v['violation_type'],
                    confidence=v['confidence'],
                    image_path=saved_path,
                    evidence_path=evidence_path,
                    timestamp=datetime.now().isoformat(),
                )
                insert_violation(record)

            st.subheader("Violation Report")
            if violations:
                for v in violations:
                    vtype = v['violation_type']
                    vname = config.VIOLATION_TYPES.get(vtype, vtype)
                    with st.container():
                        st.markdown(f"### :red[Violation: {vname}]")
                        st.markdown(f"**Confidence:** {v['confidence']:.2%}")
                        st.markdown(f"**Details:** {v.get('description', '')}")
                        st.divider()
            else:
                st.success("No violations detected in this image.")

            if plate_text:
                st.subheader("License Plate Recognition")
                st.markdown(f"**Vehicle Number:** :blue[{plate_text}]")
                st.markdown(f"**OCR Confidence:** {plate_conf:.2%}")
            elif vehicles:
                st.info("License plate could not be read. The plate may be obscured or the image resolution may be insufficient.")

            if os.path.exists(evidence_path):
                evidence_img = cv2.imread(evidence_path)
                evidence_rgb = cv2.cvtColor(evidence_img, cv2.COLOR_BGR2RGB)
                st.subheader("Evidence Image")
                st.image(evidence_rgb, use_container_width=True)

            st.download_button(
                label="Download Evidence Image",
                data=open(evidence_path, 'rb').read() if os.path.exists(evidence_path) else b'',
                file_name=f'evidence_{os.path.basename(saved_path)}',
                mime='image/jpeg',
            )


if __name__ == '__main__':
    show()
