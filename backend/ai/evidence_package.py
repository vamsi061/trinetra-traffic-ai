import os
import uuid
from datetime import datetime
from fpdf import FPDF
import config


def generate_evidence_report(image_path, detections, violations, license_plate, quality, risk_score, risk_status, source_filename=None):
    """Generate a PDF evidence package for officer review."""
    os.makedirs(config.REPORT_DIR, exist_ok=True)
    report_id = uuid.uuid4().hex[:12]
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    page_w = 190

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ——— Header ———
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 14, 'TRINETRA AI - Evidence Report', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, f'Generated: {timestamp}  |  Report ID: {report_id}', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(6)

    # ——— Separator ———
    pdf.set_draw_color(20, 60, 120)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    # ——— 1. Case Information ———
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 9, '1. Case Information', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    plate_text = license_plate.get('number', 'Not detected') if license_plate else 'Not detected'
    plate_conf = f"{license_plate.get('confidence', 0) * 100:.0f}%" if license_plate else 'N/A'
    plate_vis = license_plate.get('visibility', 'N/A') if license_plate else 'N/A'

    info_items = [
        ('Source Image', os.path.basename(image_path)),
        ('License Plate', plate_text),
        ('OCR Confidence', plate_conf),
        ('Plate Visibility', plate_vis),
        ('Overall Risk Score', str(risk_score)),
        ('Risk Level', risk_status),
    ]
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    for label, value in info_items:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(42, 7, label + ':')
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # ——— 2. Image Quality ———
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 9, '2. Image Quality Assessment', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    for label, value in [
        ('Quality Score', quality.get('score', 'N/A')),
        ('Issues', ', '.join(quality.get('issues', [])) or 'None'),
        ('Accuracy Impact', quality.get('expected_accuracy_impact', 'N/A')),
    ]:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(34, 7, label + ':')
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ——— 3. Detected Objects ———
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 9, '3. Detected Objects', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    obj_counts = [
        ('Motorcycles', sum(1 for d in detections if d.get('label') == 'motorcycle')),
        ('Cars', sum(1 for d in detections if d.get('label') == 'car')),
        ('Persons', sum(1 for d in detections if d.get('label') == 'person')),
        ('Buses', sum(1 for d in detections if d.get('label') == 'bus')),
        ('Trucks', sum(1 for d in detections if d.get('label') == 'truck')),
    ]

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(235, 240, 250)
    pdf.set_draw_color(180, 190, 210)
    col_w = [70, 30]
    pdf.cell(col_w[0], 7, 'Object Type', border=1, fill=True)
    pdf.cell(col_w[1], 7, 'Count', border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    for label, count in obj_counts:
        pdf.cell(col_w[0], 7, label, border=1)
        pdf.cell(col_w[1], 7, str(count), border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ——— 4. Detected Violations ———
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 9, '4. Detected Violations', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    if not violations:
        pdf.set_font('Helvetica', 'I', 10)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(0, 7, 'No violations detected.', new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(0, 0, 0)
        col_w = [48, 26, 24, 30, 22, 40]
        pdf.set_fill_color(235, 240, 250)
        with pdf.table(
            col_widths=col_w,
            text_align='LEFT',
            first_row_as_headings=True,
            line_height=5,
        ) as table:
            table.headers = ['Type', 'Confidence', 'Reliability',
                             'Review Status', 'Priority', 'Recommendation']
            for v in violations:
                vtype = v.get('type', v.get('violation_type', 'Unknown')).replace('_', ' ').title()
                conf = v.get('confidence_label', f"{v.get('confidence', 0)*100:.0f}%")
                rel = v.get('reliability_badge', {}).get('label', 'N/A')
                review = v.get('human_review_status', 'N/A').replace('_', ' ').title()
                pri = v.get('officer_priority', 'Medium').title()
                rec = v.get('enforcement_recommendation', 'N/A')
                row = table.row()
                row.cell(vtype)
                row.cell(conf)
                row.cell(rel)
                row.cell(review)
                row.cell(pri)
                row.cell(rec)
        pdf.ln(4)

    # ——— 5. Officer Notes ———
    pdf.set_draw_color(20, 60, 120)
    pdf.set_line_width(0.3)
    y_before = pdf.get_y()
    pdf.line(10, y_before, 200, y_before)
    pdf.ln(3)

    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 9, '5. Officer Notes', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 6, '(Add notes, findings, or enforcement decisions for review)')
    pdf.ln(5)

    # ——— 6. System Info (Footer) ———
    pdf.set_draw_color(20, 60, 120)
    pdf.set_line_width(0.3)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 4, 'TRINETRA AI - AI-Powered Traffic Enforcement Intelligence Platform', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.cell(0, 4, 'This report is for officer review. Enforcement decisions require human verification.', new_x="LMARGIN", new_y="NEXT", align='C')

    source_basename = os.path.splitext(os.path.basename(source_filename or image_path))[0]
    report_path = os.path.join(config.REPORT_DIR, f"{source_basename}_report_{report_id}.pdf")
    pdf.output(report_path)
    return report_path
