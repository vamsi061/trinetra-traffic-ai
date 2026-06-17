import os
import uuid
from datetime import datetime
import config


def generate_evidence_report(image_path, detections, violations, license_plate, quality, risk_score, risk_status):
    """Generate an HTML evidence report for officer review.

    Returns:
        path to generated report file
    """
    os.makedirs(config.REPORT_DIR, exist_ok=True)
    report_id = uuid.uuid4().hex[:12]
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    image_name = os.path.basename(image_path)
    plate_text = license_plate.get('number', 'Not detected') if license_plate else 'Not detected'
    plate_conf = f"{license_plate.get('confidence', 0) * 100:.0f}%" if license_plate else 'N/A'

    violations_html = ''
    for v in violations:
        violations_html += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;text-transform:capitalize;">{v.get('type', v.get('violation_type', 'Unknown')).replace('_', ' ')}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{v.get('confidence_label', 'N/A')}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{v.get('reliability_badge', {}).get('label', 'N/A')}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{v.get('human_review_status', 'N/A').replace('_', ' ')}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{v.get('enforcement_recommendation', 'N/A')[:60]}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>TRINETRA Evidence Report</title>
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #333; }}
h1 {{ color: #c0392b; font-size: 24px; border-bottom: 2px solid #c0392b; padding-bottom: 10px; }}
h2 {{ color: #2c3e50; font-size: 18px; margin-top: 25px; }}
table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
th {{ background: #f5f5f5; padding: 8px; text-align: left; border-bottom: 2px solid #ddd; }}
td {{ padding: 8px; border-bottom: 1px solid #eee; }}
.label {{ color: #666; font-size: 12px; }}
.value {{ font-weight: bold; }}
.footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #999; }}
</style>
</head>
<body>
<h1>TRINETRA AI — Evidence Report</h1>
<p style="color:#666;">Generated: {timestamp} | Report ID: {report_id}</p>

<h2>Case Information</h2>
<table>
    <tr><td class="label">Source Image</td><td class="value">{image_name}</td></tr>
    <tr><td class="label">License Plate</td><td class="value">{plate_text}</td></tr>
    <tr><td class="label">OCR Confidence</td><td class="value">{plate_conf}</td></tr>
    <tr><td class="label">Risk Score</td><td class="value">{risk_score}</td></tr>
    <tr><td class="label">Risk Level</td><td class="value">{risk_status}</td></tr>
</table>

<h2>Image Quality Assessment</h2>
<table>
    <tr><td class="label">Quality Score</td><td class="value">{quality.get('score', 'N/A')}</td></tr>
    <tr><td class="label">Detected Issues</td><td class="value">{', '.join(quality.get('issues', [])) or 'None'}</td></tr>
    <tr><td class="label">Expected Accuracy Impact</td><td class="value">{quality.get('expected_accuracy_impact', 'N/A')}</td></tr>
</table>

<h2>Detected Objects</h2>
<table>
    <tr><th>Object</th><th>Count</th></tr>
    <tr><td>Motorcycles</td><td>{sum(1 for d in detections if d.get('label') == 'motorcycle')}</td></tr>
    <tr><td>Cars</td><td>{sum(1 for d in detections if d.get('label') == 'car')}</td></tr>
    <tr><td>Persons</td><td>{sum(1 for d in detections if d.get('label') == 'person')}</td></tr>
    <tr><td>Buses</td><td>{sum(1 for d in detections if d.get('label') == 'bus')}</td></tr>
    <tr><td>Trucks</td><td>{sum(1 for d in detections if d.get('label') == 'truck')}</td></tr>
</table>

<h2>Detected Violations</h2>
<table>
    <tr><th>Type</th><th>Confidence</th><th>Reliability</th><th>Review Status</th><th>Recommendation</th></tr>
    {violations_html if violations_html else '<tr><td colspan="5" style="text-align:center;padding:10px;color:#999;">No violations detected</td></tr>'}
</table>

<h2>Officer Notes</h2>
<p style="border:1px solid #ddd;padding:15px;min-height:60px;border-radius:4px;color:#999;">
<em>Add notes here for review...</em></p>

<div class="footer">
    <p>TRINETRA AI — AI-Powered Traffic Enforcement Intelligence Platform</p>
    <p>This report is for officer review purposes only. Enforcement decisions require human verification.</p>
</div>
</body>
</html>"""

    report_path = os.path.join(config.REPORT_DIR, f"evidence_{report_id}.html")
    with open(report_path, 'w') as f:
        f.write(html)

    return report_path
