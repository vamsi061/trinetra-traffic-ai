import requests
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config

API_URL = "http://0.0.0.0:8000/api/detect"
SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")
UPLOAD_DIR = config.UPLOAD_DIR
EVIDENCE_DIR = config.EVIDENCE_DIR
REPORT_DIR = config.REPORT_DIR

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EVIDENCE_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# Clear old files
for d in [UPLOAD_DIR, EVIDENCE_DIR, REPORT_DIR]:
    for f in os.listdir(d):
        fp = os.path.join(d, f)
        try:
            os.remove(fp)
        except:
            pass

# Define expected behaviors per image
# Each entry: (filename, expected_violation_types[], expected_plate_substr, desc)
TEST_CASES = [
    # Helmet cases
    ("HELMET_MISSING_001.png", ["NO_HELMET"], None, "Rider without helmet"),
    ("HELMET_MISSING_002.png", ["NO_HELMET"], None, "Rider without helmet"),
    ("HELMET_MISSING_003.png", ["NO_HELMET"], None, "Rider without helmet"),
    ("HELMET_MISSING_004.png", ["NO_HELMET"], None, "Rider without helmet"),
    ("HELMET_MISSING_005.png", ["NO_HELMET"], None, "Rider without helmet (may also detect overloading if 4+ riders)"),
    ("BikesHelmets01.png", [], None, "Bike with helmet — should be COMPLIANT"),
    ("BikesHelmets02.png", [], None, "Bike with helmet — may detect NO_HELMET if rider head obscured"),
    ("BikesHelmets03.png", [], None, "Bike with helmet — should be COMPLIANT"),
    ("BikesHelmets04.png", [], None, "Bike with helmet — should be COMPLIANT"),
    # Overloading / triple riding
    ("OVERLOADING_001.jpg", ["TRIPLE_RIDING"], None, "3 riders on one motorcycle"),
    ("TRIPLE_RIDING_001.jpeg", ["TRIPLE_RIDING"], None, "Triple riding"),
    ("TRIPLE_RIDING_002.jpg", [], None, "Three persons but no motorcycle detected (YOLO limitation)"),
    # Parking
    ("ILLEGAL PARKING_001.png", ["POSSIBLE_ILLEGAL_PARKING"], "6149", "Illegal parking with plate"),
    ("ILLEGAL PARKING_002.png", ["POSSIBLE_ILLEGAL_PARKING"], None, "Illegal parking"),
    # OCR / plate
    ("OCR_CLEAR_001.png", [], None, "Clear plate"),
    ("OCR_CLEAR_002.png", [], None, "Clear plate"),
    # Edge cases
    ("PEDESTRIAN_001.png", [], None, "Pedestrian only — no violations"),
    ("CROWDED_001.png", [], None, "Crowded scene — no specific violations"),
    ("LOWLIGHT_001.png", [], None, "Low light — may have triple riding if riders visible"),
    ("RAIN_001.png", [], None, "Rain conditions — associations may be unreliable"),
]

results = []
passed = 0
failed = 0

for filename, expected_violations, expected_plate, desc in TEST_CASES:
    filepath = os.path.join(SAMPLES_DIR, filename)
    if not os.path.exists(filepath):
        results.append((filename, "SKIP", f"File not found: {filepath}"))
        continue

    print(f"\n{'='*60}")
    print(f"TEST: {filename}")
    print(f"  Description: {desc}")
    print(f"  Expected violations: {expected_violations or 'none (compliant)'}")

    try:
        with open(filepath, "rb") as f:
            resp = requests.post(API_URL, files={"file": (filename, f, "image/png")}, timeout=120)
    except requests.exceptions.RequestException as e:
        results.append((filename, "FAIL", f"Request failed: {e}"))
        failed += 1
        continue

    if resp.status_code != 200:
        results.append((filename, "FAIL", f"HTTP {resp.status_code}: {resp.text[:200]}"))
        failed += 1
        continue

    data = resp.json()
    detected_types = [v["type"] for v in data.get("violations", [])]
    compliance = data.get("compliance_status", "NONE")
    plate = data.get("license_plate")
    plate_text = plate.get("number", "") if plate else ""
    evidence_img = data.get("evidence_path", "")
    evidence_report = data.get("evidence_report", "")
    risk = data.get("risk_status", "NONE")
    helmet_model = data.get("helmet_model", {})

    # Check evidence filenames contain original image name
    img_basename = os.path.splitext(filename)[0]
    ev_img_ok = img_basename in evidence_img if evidence_img else False
    ev_report_ok = img_basename in evidence_report if evidence_report else False

    # Check violations match expectations
    misses = [v for v in expected_violations if v not in detected_types]
    extras = [v for v in detected_types if v not in expected_violations]

    status = "PASS"
    issues = []

    if misses:
        issues.append(f"MISSING expected: {misses}")
        status = "FAIL"
    if extras:
        issues.append(f"EXTRA (ok): {extras}")
    if compliance == "COMPLIANT" and misses:
        issues.append("Compliance=COMPLIANT but expected violations missing")
    if not ev_img_ok:
        issues.append(f"Evidence image name doesn't contain '{img_basename}' (got: {evidence_img})")
    if not ev_report_ok:
        issues.append(f"Report name doesn't contain '{img_basename}' (got: {evidence_report})")
    if expected_plate and plate_text:
        if expected_plate not in plate_text.upper():
            issues.append(f"Plate '{plate_text}' doesn't contain '{expected_plate}'")

    result_line = (
        f"  Status: {status}\n"
        f"  Detected violations: {detected_types}\n"
        f"  Compliance: {compliance}\n"
        f"  Risk: {risk}\n"
        f"  Plate: '{plate_text}'\n"
        f"  Evidence image: {evidence_img}\n"
        f"  Evidence report: {evidence_report}\n"
        f"  Helmet model: {helmet_model.get('model_name', 'N/A')} (loaded={helmet_model.get('loaded', False)})\n"
    )
    if misses:
        result_line += f"  ** MISSING: {misses}\n"
    if extras:
        result_line += f"  ** EXTRA: {extras}\n"

    print(result_line)

    if status == "PASS":
        passed += 1
    else:
        failed += 1

    results.append((filename, status, issues))

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print(f"Total: {len(TEST_CASES)}, Passed: {passed}, Failed: {failed}")
for filename, status, issues in results:
    print(f"  [{status}] {filename}: {'; '.join(issues) if issues else 'OK'}")
