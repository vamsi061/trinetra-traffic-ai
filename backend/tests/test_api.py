import pytest
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.models import ViolationRecord
from database.db import insert_violation


@pytest.fixture(autouse=True)
def seed_data():
    for i in range(3):
        insert_violation(ViolationRecord(
            vehicle_number=f"KA01AB{i}234",
            vehicle_type="motorcycle",
            violation_type="NO_HELMET",
            confidence=0.9 - i * 0.1,
            image_path=f"/tmp/img{i}.jpg",
            evidence_path=f"/tmp/ev{i}.jpg",
        ))
    insert_violation(ViolationRecord(
        vehicle_number="MH12DE3456",
        vehicle_type="motorcycle",
        violation_type="TRIPLE_RIDING",
        confidence=0.85,
        image_path="/tmp/triple.jpg",
        evidence_path="/tmp/ev_triple.jpg",
    ))


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_body(self, client):
        resp = client.get("/api/health")
        data = resp.json()
        assert data['status'] == 'operational'
        assert data['service'] == 'TRINETRA AI'


class TestDetectEndpoint:
    def test_detect_no_file_422(self, client):
        resp = client.post("/api/detect")
        assert resp.status_code == 422

    def test_detect_text_file_400(self, client):
        resp = client.post(
            "/api/detect",
            files={"file": ("test.txt", b"not an image", "text/plain")}
        )
        assert resp.status_code == 400

    def test_detect_with_image_200(self, client):
        path = os.path.join(os.path.dirname(__file__), 'samples', 'test1_no_helmet.jpg')
        if not os.path.exists(path):
            pytest.skip("Sample image not found")
        with open(path, 'rb') as f:
            resp = client.post("/api/detect", files={"file": ("test.jpg", f, "image/jpeg")})
        assert resp.status_code == 200

    def test_detect_result_fields(self, client):
        path = os.path.join(os.path.dirname(__file__), 'samples', 'test1_no_helmet.jpg')
        if not os.path.exists(path):
            pytest.skip("Sample image not found")
        with open(path, 'rb') as f:
            resp = client.post("/api/detect", files={"file": ("test.jpg", f, "image/jpeg")})
        data = resp.json()
        assert 'success' in data
        assert 'detections' in data
        assert 'violations' in data
        assert 'license_plate' in data
        assert 'evidence_path' in data


class TestViolationsEndpoints:
    def test_list_violations(self, client):
        resp = client.get("/api/violations")
        assert resp.status_code == 200
        data = resp.json()
        assert 'total' in data
        assert 'violations' in data
        assert data['total'] >= 4

    def test_list_violations_filter_type(self, client):
        resp = client.get("/api/violations?violation_type=NO_HELMET")
        data = resp.json()
        for v in data['violations']:
            assert v['violation_type'] == 'NO_HELMET'

    def test_list_violations_filter_vehicle(self, client):
        resp = client.get("/api/violations?vehicle_number=KA01")
        data = resp.json()
        for v in data['violations']:
            assert 'KA01' in v['vehicle_number']

    def test_list_violations_pagination(self, client):
        resp = client.get("/api/violations?limit=2")
        data = resp.json()
        assert len(data['violations']) <= 2
        assert data['total'] >= 2

    def test_recent_violations(self, client):
        resp = client.get("/api/violations/recent")
        assert resp.status_code == 200
        data = resp.json()
        assert 'violations' in data
        assert len(data['violations']) > 0

    def test_violation_stats(self, client):
        resp = client.get("/api/violations/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert 'total' in data
        assert 'no_helmet' in data
        assert 'triple_riding' in data
        assert 'unique_vehicles' in data
        assert data['total'] >= 4

    def test_violation_analytics(self, client):
        resp = client.get("/api/violations/analytics")
        assert resp.status_code == 200
        data = resp.json()
        assert 'by_type' in data
        assert 'by_day' in data
        assert 'repeat_offenders' in data
        assert 'monthly_trend' in data

    def test_evidence_not_found_404(self, client):
        resp = client.get("/api/evidence/nonexistent.jpg")
        assert resp.status_code == 404

    def test_evidence_found(self, client):
        resp = client.get("/api/evidence/ev0.jpg")
        if resp.status_code == 200:
            assert resp.headers['content-type'].startswith('image/')
        else:
            assert resp.status_code == 404
