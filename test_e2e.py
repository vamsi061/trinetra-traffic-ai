"""End-to-end test for TRINETRA AI detection pipeline.

Usage:
    python test_e2e.py
    python test_e2e.py -v
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), 'backend', 'tests', 'samples')
PASS = 0
FAIL = 0
VERBOSE = '-v' in sys.argv


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}" + (f"  -- {detail}" if detail else ""))


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    check("health endpoint", data['status'] == 'operational', str(data))


def test_detect_no_helmet():
    path = os.path.join(SAMPLES_DIR, "test1_no_helmet.jpg")
    if not os.path.exists(path):
        print("  ⚠ test1_no_helmet.jpg missing - skipping"); return
    with open(path, 'rb') as f:
        resp = client.post("/api/detect", files={"file": ("test1.jpg", f, "image/jpeg")})
    check("status 200", resp.status_code == 200)
    data = resp.json()
    check("detections present", len(data['detections']) > 0, str(data['detections']))
    vtypes = [v['type'] for v in data['violations']]
    has_nh = 'NO_HELMET' in vtypes
    check("NO_HELMET violation", has_nh, str(vtypes))


def test_detect_triple_riding():
    path = os.path.join(SAMPLES_DIR, "test3_triple_riding.jpg")
    if not os.path.exists(path):
        print("  ⚠ test3_triple_riding.jpg missing - skipping"); return
    with open(path, 'rb') as f:
        resp = client.post("/api/detect", files={"file": ("test3.jpg", f, "image/jpeg")})
    check("status 200", resp.status_code == 200)
    data = resp.json()
    vtypes = [v['type'] for v in data['violations']]
    has_tr = 'TRIPLE_RIDING' in vtypes
    check("TRIPLE_RIDING violation", has_tr, str(vtypes))


def test_detect_compliant():
    path = os.path.join(SAMPLES_DIR, "test5_compliant.jpg")
    if not os.path.exists(path):
        print("  ⚠ test5_compliant.jpg missing - skipping"); return
    with open(path, 'rb') as f:
        resp = client.post("/api/detect", files={"file": ("test5.jpg", f, "image/jpeg")})
    check("status 200", resp.status_code == 200)
    data = resp.json()
    check("no violations for compliant", len(data['violations']) == 0, str(data['violations']))


def test_detect_car_plate():
    path = os.path.join(SAMPLES_DIR, "test4_car_plate.jpg")
    if not os.path.exists(path):
        print("  ⚠ test4_car_plate.jpg missing - skipping"); return
    with open(path, 'rb') as f:
        resp = client.post("/api/detect", files={"file": ("test4.jpg", f, "image/jpeg")})
    check("status 200", resp.status_code == 200)
    data = resp.json()
    plate = data.get('license_plate')
    has_plate = plate is not None and len(plate.get('number', '')) > 0
    check("license plate extracted", has_plate, str(plate))


def test_violation_endpoints():
    resp = client.get("/api/violations")
    check("GET /api/violations", resp.status_code == 200)
    data = resp.json()
    check("total field", 'total' in data)
    check("violations list", 'violations' in data)

    resp = client.get("/api/violations/stats")
    check("GET /api/violations/stats", resp.status_code == 200)
    data = resp.json()
    check("stats total", 'total' in data)
    check("stats no_helmet", 'no_helmet' in data)
    check("stats triple_riding", 'triple_riding' in data)

    resp = client.get("/api/violations/recent")
    check("GET /api/violations/recent", resp.status_code == 200)

    resp = client.get("/api/violations/analytics")
    check("GET /api/violations/analytics", resp.status_code == 200)
    data = resp.json()
    check("analytics by_type", 'by_type' in data)
    check("analytics by_day", 'by_day' in data)
    check("analytics repeat_offenders", 'repeat_offenders' in data)
    check("analytics monthly_trend", 'monthly_trend' in data)


def test_evidence_retrieval():
    path = os.path.join(SAMPLES_DIR, "test1_no_helmet.jpg")
    if not os.path.exists(path):
        return
    with open(path, 'rb') as f:
        resp = client.post("/api/detect", files={"file": ("test1.jpg", f, "image/jpeg")})
    data = resp.json()
    ev_path = data.get('evidence_path', '')
    if ev_path:
        resp = client.get(f"/api/evidence/{os.path.basename(ev_path)}")
        check("evidence retrieval", resp.status_code == 200)
        check("evidence is image", resp.headers['content-type'].startswith('image/'))
    else:
        print("  ⚠ no evidence_path - skipping")


def test_error_handling():
    resp = client.post("/api/detect", files={"file": ("bad.txt", b"xxx", "text/plain")})
    check("rejects non-image", resp.status_code == 400)

    resp = client.get("/api/evidence/missing.jpg")
    check("missing evidence 404", resp.status_code == 404)


def run_all():
    print("\n" + "=" * 60)
    print("  TRINETRA AI — End-to-End Test Suite")
    print("=" * 60)

    tests = [
        ("Health Check", test_health),
        ("No Helmet Detection", test_detect_no_helmet),
        ("Triple Riding Detection", test_detect_triple_riding),
        ("Compliant Rider", test_detect_compliant),
        ("Car Plate OCR", test_detect_car_plate),
        ("Violation API Endpoints", test_violation_endpoints),
        ("Evidence Retrieval", test_evidence_retrieval),
        ("Error Handling", test_error_handling),
    ]

    for name, func in tests:
        print(f"\n── {name} ──")
        try:
            func()
        except Exception as e:
            global FAIL
            FAIL += 1
            print(f"  ✗ EXCEPTION: {e}")

    total = PASS + FAIL
    print(f"\n{'=' * 60}")
    print(f"  {PASS}/{total} passed  ({FAIL} failed)")
    print(f"{'=' * 60}\n")
    return FAIL == 0


if __name__ == '__main__':
    sys.exit(0 if run_all() else 1)
