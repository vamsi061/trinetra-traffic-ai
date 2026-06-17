import os
import uuid
from datetime import datetime
from fpdf import FPDF
import config


def generate_evidence_report(image_path, detections, violations, license_plate, quality, risk_score, risk_status):
    """Generate a PDF evidence package for officer review."""
    os.makedirs(config.REPORT_DIR, exist_ok=True)
    report_id = uuid.uuid4().hex[:12]
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(192, 57, 43)
    pdf.cell(0, 12, 'TRINETRA AI - Evidence Report', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f'Generated: {timestamp}  |  Report ID: {report_id}', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(5)

    # Case Information
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 8, 'Case Information', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)

    plate_text = license_plate.get('number', 'Not detected') if license_plate else 'Not detected'
    plate_conf = f"{license_plate.get('confidence', 0) * 100:.0f}%" if license_plate else 'N/A'
    plate_vis = license_plate.get('visibility', 'N/A') if license_plate else 'N/A'

    info_lines = [
        f'Source Image: {os.path.basename(image_path)}',
        f'License Plate: {plate_text}',
        f'OCR Confidence: {plate_conf}',
        f'Plate Visibility: {plate_vis}',
        f'Overall Risk Score: {risk_score}',
        f'Risk Level: {risk_status}',
    ]
    for line in info_lines:
        pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Image Quality
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 8, 'Image Quality Assessment', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    q_lines = [
        f'Quality Score: {quality.get("score", "N/A")}',
        f'Detected Issues: {", ".join(quality.get("issues", [])) or "None"}',
        f'Expected Accuracy Impact: {quality.get("expected_accuracy_impact", "N/A")}',
    ]
    for line in q_lines:
        pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Detected Objects
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 8, 'Detected Objects', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)

    mc_count = sum(1 for d in detections if d.get('label') == 'motorcycle')
    car_count = sum(1 for d in detections if d.get('label') == 'car')
    person_count = sum(1 for d in detections if d.get('label') == 'person')
    bus_count = sum(1 for d in detections if d.get('label') == 'bus')
    truck_count = sum(1 for d in detections if d.get('label') == 'truck')

    # Table header
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(60, 7, 'Object Type', border=1, fill=True)
    pdf.cell(30, 7, 'Count', border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font('Helvetica', '', 10)
    for label, count in [('Motorcycles', mc_count), ('Cars', car_count), ('Persons', person_count),
                          ('Buses', bus_count), ('Trucks', truck_count)]:
        pdf.cell(60, 6, label, border=1)
        pdf.cell(30, 6, str(count), border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Violations
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 8, 'Detected Violations', new_x="LMARGIN", new_y="NEXT")

    if not violations:
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, 'No violations detected.', new_x="LMARGIN", new_y="NEXT")
    else:
        # Table header
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_fill_color(245, 245, 245)
        col_w = [40, 28, 22, 28, 22, 30]
        headers = ['Type', 'Confidence', 'Reliability', 'Review', 'Priority', 'Recommendation']
        for i, h in enumerate(headers):
            pdf.cell(col_w[i], 7, h, border=1, fill=True)
        pdf.ln()

        pdf.set_font('Helvetica', '', 7)
        for v in violations:
            vtype = v.get('type', v.get('violation_type', 'Unknown')).replace('_', ' ').capitalize()
            conf = v.get('confidence_label', 'N/A')
            rel = v.get('reliability_badge', {}).get('label', 'N/A')
            review = v.get('human_review_status', 'N/A').replace('_', ' ')
            pri = v.get('officer_priority', 'MEDIUM')
            rec = v.get('enforcement_recommendation', 'N/A')[:45]
            vals = [vtype, conf, rel, review, pri, rec]
            for i, val in enumerate(vals):
                pdf.cell(col_w[i], 6, val, border=1)
            pdf.ln()

    pdf.ln(5)

    # Officer Notes section
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 8, 'Officer Notes', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(200, 200, 200)
    pdf.cell(0, 6, '(Add notes for review)', new_x="LMARGIN", new_y="NEXT")

    pdf.ln(10)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, 'TRINETRA AI - AI-Powered Traffic Enforcement Intelligence Platform', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.cell(0, 5, 'This report is for officer review. Enforcement decisions require human verification.', new_x="LMARGIN", new_y="NEXT", align='C')

    report_path = os.path.join(config.REPORT_DIR, f"evidence_{report_id}.pdf")
    pdf.output(report_path)
    return report_path
