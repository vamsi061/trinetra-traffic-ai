import os
import uuid
import re
from datetime import datetime
from fpdf import FPDF
import config


def _sanitize(text):
    """Replace characters outside Latin-1 range that fpdf Helvetica can't render."""
    if not isinstance(text, str):
        return str(text)
    replacements = {
        '\u2014': '-', '\u2013': '-', '\u2022': '*', '\u2026': '...',
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u00b7': '*', '\u2022': '*', '\u2026': '...', '\u00a0': ' ',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode('latin-1', errors='replace').decode('latin-1')


def _safe_cell(pdf, *args, **kwargs):
    """pdf.cell with automatic text sanitization."""
    if len(args) >= 3:
        args = list(args)
        args[2] = _sanitize(args[2])
    if 'text' in kwargs:
        kwargs['text'] = _sanitize(kwargs['text'])
    return pdf.cell(*args, **kwargs)


def _safe_multi_cell(pdf, *args, **kwargs):
    """pdf.multi_cell with automatic text sanitization."""
    if len(args) >= 3:
        args = list(args)
        args[2] = _sanitize(args[2])
    if 'text' in kwargs:
        kwargs['text'] = _sanitize(kwargs['text'])
    return pdf.multi_cell(*args, **kwargs)


DETECTION_SOURCE_LABELS = {
    'NO_HELMET': 'YOLOv8 Helmet Model',
    'HELMET_ASSESSMENT_UNCERTAIN': 'Helmet Model (Low Confidence / HSV)',
    'TRIPLE_RIDING': 'Rider Association Scoring',
    'MOTORCYCLE_OVERLOADING': 'Rider Association Scoring',
    'MOTORCYCLE_EXTREME_OVERLOADING': 'Rider Association Scoring',
    'POSSIBLE_ILLEGAL_PARKING': 'Spatial Analysis + Geometric Rules',
    'SEATBELT_VIOLATION': 'YOLOv8 + HSV Analysis',
    'WRONG_SIDE_DRIVING': 'Lane Orientation Analysis',
    'RED_LIGHT_VIOLATION': 'Traffic Light Color Detection',
    'STOP_LINE_VIOLATION': 'Hough Transform + Geometric Validation',
    'POSSIBLE_STOP_LINE_VIOLATION': 'Hough Transform + Geometric Validation',
}


def _detection_source(v):
    return v.get('detection_source') or DETECTION_SOURCE_LABELS.get(
        v.get('violation_type', ''), 'Automated Detection'
    )


def generate_evidence_report(image_path, detections, violations, license_plate, quality, risk_score, risk_status, source_filename=None, enhancement_report=None, quality_analysis=None, scene_understanding=None, ai_review_panel=None):
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
    _safe_cell(pdf, 0, 14, 'TRINETRA AI - Evidence Report', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(80, 80, 80)
    _safe_cell(pdf, 0, 6, f'Generated: {timestamp}  |  Report ID: {report_id}', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(6)

    # ——— Separator ———
    pdf.set_draw_color(20, 60, 120)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    # ——— 1. Case Information ———
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(20, 60, 120)
    _safe_cell(pdf, 0, 9, '1. Case Information', new_x="LMARGIN", new_y="NEXT")
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
        _safe_cell(pdf, 42, 7, label + ':')
        pdf.set_font('Helvetica', '', 10)
        _safe_cell(pdf, 0, 7, value, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # ——— 2. Image Quality ———
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(20, 60, 120)
    _safe_cell(pdf, 0, 9, '2. Image Quality Assessment', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    for label, value in [
        ('Quality Score', quality.get('score', 'N/A')),
        ('Issues', ', '.join(quality.get('issues', [])) or 'None'),
        ('Accuracy Impact', quality.get('expected_accuracy_impact', 'N/A')),
    ]:
        pdf.set_font('Helvetica', 'B', 10)
        _safe_cell(pdf, 34, 7, label + ':')
        pdf.set_font('Helvetica', '', 10)
        _safe_cell(pdf, 0, 7, value, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ——— 2b. Image Enhancement ———
    if enhancement_report or quality_analysis:
        pdf.set_font('Helvetica', 'B', 13)
        pdf.set_text_color(20, 60, 120)
        _safe_cell(pdf, 0, 9, '2a. Image Enhancement Pipeline', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(0, 0, 0)

        if enhancement_report:
            steps_applied = enhancement_report.get('steps_applied', [])
            failover = enhancement_report.get('failover_used', False)
            quality_delta = enhancement_report.get('quality_delta', 0)
            fallback_reason = enhancement_report.get('fallback_reason', '')

            pdf.set_font('Helvetica', 'B', 10)
            _safe_cell(pdf, 0, 7, 'Enhancement Steps:', new_x="LMARGIN", new_y="NEXT")
            pdf.set_font('Helvetica', '', 10)
            if steps_applied:
                for step in steps_applied:
                    _safe_cell(pdf, 0, 6, f'  - {step}', new_x="LMARGIN", new_y="NEXT")
            else:
                _safe_cell(pdf, 0, 6, '  (None - image already good quality)', new_x="LMARGIN", new_y="NEXT")

            if failover:
                pdf.set_font('Helvetica', 'I', 9)
                pdf.set_text_color(200, 100, 30)
                _safe_cell(pdf, 0, 6, f'  Fallback mode: {fallback_reason}', new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(0, 0, 0)

            pdf.ln(1)
            pdf.set_font('Helvetica', '', 10)
            quality_change = f'{quality_delta:+.1f}%' if quality_delta else 'N/A'
            for label, value in [
                ('Quality Change', quality_change),
                ('Failover Used', 'Yes' if failover else 'No'),
            ]:
                pdf.set_font('Helvetica', 'B', 10)
                _safe_cell(pdf, 42, 7, label + ':')
                pdf.set_font('Helvetica', '', 10)
                _safe_cell(pdf, 0, 7, value, new_x="LMARGIN", new_y="NEXT")

        if quality_analysis:
            pdf.ln(1)
            pdf.set_font('Helvetica', 'B', 10)
            _safe_cell(pdf, 0, 7, 'Quality Metrics:', new_x="LMARGIN", new_y="NEXT")
            pdf.set_font('Helvetica', '', 10)
            for metric in ['brightness', 'contrast', 'sharpness', 'noise']:
                val = quality_analysis.get(metric)
                if val is not None:
                    if metric == 'noise':
                        status = 'Poor' if val > 0.4 else ('Fair' if val > 0.2 else 'Good')
                    else:
                        status = 'Good' if val > 0.4 else ('Fair' if val > 0.2 else 'Poor')
                    _safe_cell(pdf, 0, 6, f'  {metric.title()}: {val:.2f} ({status})', new_x="LMARGIN", new_y="NEXT")
            issues = quality_analysis.get('issues', [])
            if issues:
                _safe_cell(pdf, 0, 6, f'  Detected Issues: {", ".join(issues)}', new_x="LMARGIN", new_y="NEXT")

        pdf.ln(3)

    # ——— 3. Detected Objects ———
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(20, 60, 120)
    _safe_cell(pdf, 0, 9, '3. Detected Objects', new_x="LMARGIN", new_y="NEXT")
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
    _safe_cell(pdf, col_w[0], 7, 'Object Type', border=1, fill=True)
    _safe_cell(pdf, col_w[1], 7, 'Count', border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    for label, count in obj_counts:
        _safe_cell(pdf, col_w[0], 7, label, border=1)
        _safe_cell(pdf, col_w[1], 7, str(count), border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ——— 3b. Scene Breakdown ———
    if scene_understanding and scene_understanding.get('scene_breakdown'):
        sb = scene_understanding['scene_breakdown']
        pdf.set_font('Helvetica', 'B', 13)
        pdf.set_text_color(20, 60, 120)
        _safe_cell(pdf, 0, 9, '3b. Scene Composition', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        sb_items = [
            ('Motorcycles', sb.get('motorcycles', 0)),
            ('Cars', sb.get('cars', 0)),
            ('Buses', sb.get('buses', 0)),
            ('Trucks', sb.get('trucks', 0)),
            ('Visible Persons', sb.get('visible_persons', 0)),
            ('Associated Riders', sb.get('associated_riders', 0)),
            ('Pedestrians', sb.get('pedestrians', 0)),
        ]
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_fill_color(235, 240, 250)
        pdf.set_draw_color(180, 190, 210)
        _safe_cell(pdf, col_w[0], 7, 'Category', border=1, fill=True)
        _safe_cell(pdf, col_w[1], 7, 'Count', border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(0, 0, 0)
        for label, count in sb_items:
            _safe_cell(pdf, col_w[0], 7, label, border=1)
            _safe_cell(pdf, col_w[1], 7, str(count), border=1, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # ——— 3c. Primary Finding ———
    primary_finding = scene_understanding.get('primary_finding') if scene_understanding else None
    if primary_finding:
        pdf.set_font('Helvetica', 'B', 13)
        pdf.set_text_color(180, 40, 20)
        _safe_cell(pdf, 0, 9, '3c. Primary Finding', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(0, 0, 0)
        _safe_cell(pdf, 0, 7, primary_finding.get('type', primary_finding.get('violation_type', 'Unknown')), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('Helvetica', '', 10)
        for label, value in [
            ('Type', primary_finding.get('violation_type', 'N/A')),
            ('Confidence', f"{primary_finding.get('confidence', 0)*100:.1f}%"),
            ('Evidence Score', f"{primary_finding.get('evidence_score', 0)*100:.1f}%"),
            ('Priority Score', f"{primary_finding.get('priority_score', 0)*100:.1f}%"),
            ('Reason', primary_finding.get('reason', 'N/A')),
            ('Review Required', 'Yes' if primary_finding.get('needs_review') else 'No'),
            ('Enforcement', primary_finding.get('enforcement_recommendation', 'N/A')),
        ]:
            pdf.set_font('Helvetica', 'B', 10)
            _safe_cell(pdf, 36, 6, label + ':')
            pdf.set_font('Helvetica', '', 10)
            _safe_cell(pdf, 0, 6, value, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # ——— 4. Observed Findings ———
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(20, 60, 120)
    _safe_cell(pdf, 0, 9, '4. Observed Findings', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    if not violations:
        pdf.set_font('Helvetica', 'I', 10)
        pdf.set_text_color(60, 60, 60)
        _safe_cell(pdf, 0, 7, 'No findings detected.', new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(0, 0, 0)
        col_w = [32, 22, 18, 30, 18, 18, 52]
        pdf.set_fill_color(235, 240, 250)
        with pdf.table(
            col_widths=col_w,
            text_align='LEFT',
            first_row_as_headings=True,
            line_height=5,
        ) as table:
            hr = table.row()
            hr.cell('Finding')
            hr.cell('Vehicle')
            hr.cell('Conf.')
            hr.cell('Detection Source')
            hr.cell('Review')
            hr.cell('Prior.')
            hr.cell('Recommendation')
            for v in violations:
                suppressed = v.get('_suppressed', False)
                is_primary = v.get('_is_primary', False)
                vtype = v.get('display_type', v.get('type', v.get('violation_type', 'Unknown')).replace('_', ' ').title())
                invo = v.get('involved_objects', [])
                if invo:
                    vehicle_str = invo[0].replace('_', ' ').title()
                else:
                    desc = v.get('description', '')
                    vehicle_str = desc.split(' ')[0].replace('_', ' ').title() if desc else '-'
                raw_conf = v.get('confidence_label', '')
                if raw_conf in ('HIGH CONFIDENCE',):
                    conf = 'High'
                elif raw_conf in ('MEDIUM CONFIDENCE',):
                    conf = 'Medium'
                elif raw_conf in ('LOW CONFIDENCE',):
                    conf = 'Low'
                else:
                    conf = f"{v.get('confidence', 0)*100:.0f}%"
                source = _detection_source(v)
                review = v.get('human_review_status', 'N/A').replace('_', ' ').title()
                pri = v.get('officer_priority', 'Medium').title()
                rec = v.get('enforcement_recommendation', 'N/A')
                if is_primary:
                    vtype = f'[PRIMARY] {vtype}'
                if suppressed:
                    vtype = f'{vtype} (SUPPRESSED)'
                    pdf.set_text_color(160, 160, 160)
                row = table.row()
                row.cell(vtype)
                row.cell(vehicle_str)
                row.cell(conf)
                row.cell(source)
                row.cell(review)
                row.cell(pri)
                row.cell(rec)
                if suppressed:
                    pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

    # ——— 5. Scene Understanding (Assessment) ———
    if scene_understanding:
        pdf.set_draw_color(20, 60, 120)
        pdf.set_line_width(0.3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        pdf.set_font('Helvetica', 'B', 13)
        pdf.set_text_color(20, 60, 120)
        _safe_cell(pdf, 0, 9, '5. Scene Assessment', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        narrative = scene_understanding.get('narrative', '')
        analysis_type = scene_understanding.get('analysis_type', 'template')
        reasoning_conf = scene_understanding.get('confidence', 0)

        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(0, 0, 0)
        if narrative:
            pdf.set_font('Helvetica', 'I', 10)
            _safe_multi_cell(pdf, 0, 6, narrative)
            pdf.ln(2)

        # Include detected object counts alongside narrative for cross-reference
        scene_breakdown = scene_understanding.get('scene_breakdown', {})
        if scene_breakdown:
            pdf.set_font('Helvetica', '', 8)
            pdf.set_text_color(80, 80, 80)
            parts = []
            for k in ('motorcycles', 'cars', 'buses', 'trucks', 'visible_persons', 'bicycles'):
                v = scene_breakdown.get(k)
                if v is not None and v > 0:
                    parts.append(f'{k.replace("_", " ").title()}: {v}')
            if parts:
                _safe_cell(pdf, 0, 5, 'Detected objects: ' + ' | '.join(parts), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            pdf.set_text_color(0, 0, 0)

        for label, value in [
            ('Assessment Method', 'Florence-2' if analysis_type == 'florence-2' else 'Template-based'),
            ('Assessment Confidence', f'{reasoning_conf*100:.0f}%'),
        ]:
            pdf.set_font('Helvetica', 'B', 10)
            _safe_cell(pdf, 42, 7, label + ':')
            pdf.set_font('Helvetica', '', 10)
            _safe_cell(pdf, 0, 7, value, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # ——— 6. Automated Assessment Summary ———
    if ai_review_panel:
        pdf.set_draw_color(20, 60, 120)
        pdf.set_line_width(0.3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        pdf.set_font('Helvetica', 'B', 13)
        pdf.set_text_color(20, 60, 120)
        _safe_cell(pdf, 0, 9, '6. Automated Assessment Summary', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        v_status = ai_review_panel.get('verification_status', 'N/A').replace('_', ' ').title()
        v_verified = ai_review_panel.get('violations_verified', 0)
        v_unverified = ai_review_panel.get('violations_unverified', 0)
        avg_conf = ai_review_panel.get('average_verification_confidence', 0)
        enforcement = ai_review_panel.get('enforcement_readiness', 'N/A').replace('_', ' ').title()

        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(0, 0, 0)
        for label, value in [
            ('Assessment Status', v_status),
            ('Verified Findings', str(v_verified)),
            ('Unverified Findings', str(v_unverified)),
            ('Avg Assessment Confidence', f'{avg_conf*100:.0f}%' if avg_conf else 'N/A'),
            ('Enforcement Readiness', enforcement),
        ]:
            pdf.set_font('Helvetica', 'B', 10)
            _safe_cell(pdf, 52, 7, label + ':')
            pdf.set_font('Helvetica', '', 10)
            _safe_cell(pdf, 0, 7, value, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # ——— 7. Officer Notes ———
    pdf.set_draw_color(20, 60, 120)
    pdf.set_line_width(0.3)
    y_before = pdf.get_y()
    pdf.line(10, y_before, 200, y_before)
    pdf.ln(3)

    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(20, 60, 120)
    _safe_cell(pdf, 0, 9, '7. Officer Notes', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(100, 100, 100)
    _safe_multi_cell(pdf, 0, 6, '(Add notes, findings, or enforcement decisions for review)')
    pdf.ln(5)

    # ——— 8. System Info (Footer) ———
    pdf.set_draw_color(20, 60, 120)
    pdf.set_line_width(0.3)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(80, 80, 80)
    _safe_cell(pdf, 0, 4, 'TRINETRA AI - AI-Powered Traffic Enforcement Intelligence Platform', new_x="LMARGIN", new_y="NEXT", align='C')
    _safe_cell(pdf, 0, 4, 'This report is for officer review. Enforcement decisions require human verification.', new_x="LMARGIN", new_y="NEXT", align='C')

    source_basename = os.path.splitext(os.path.basename(source_filename or image_path))[0]
    report_path = os.path.join(config.REPORT_DIR, f"{source_basename}_report_{report_id}.pdf")
    pdf.output(report_path)
    return report_path
