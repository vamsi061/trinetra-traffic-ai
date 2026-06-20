import requests
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

API_URL = "http://0.0.0.0:8000/api/detect"
SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")

FAILING = [
    "HELMET_MISSING_001.png",
    "BikesHelmets02.png",
    "OVERLOADING_001.jpg",
    "TRIPLE_RIDING_002.jpg",
    "ILLEGAL PARKING_001.png",
    "ILLEGAL PARKING_002.png",
    "LOWLIGHT_001.png",
    "RAIN_001.png",
    "HELMET_MISSING_005.png",
]

for filename in FAILING:
    filepath = os.path.join(SAMPLES_DIR, filename)
    if not os.path.exists(filepath):
        print(f"\n=== {filename} === FILE NOT FOUND")
        continue

    print(f"\n{'='*70}")
    print(f"=== {filename} ===")
    print('='*70)

    with open(filepath, "rb") as f:
        resp = requests.post(API_URL, files={"file": (filename, f, "image/png")}, timeout=120)

    data = resp.json()

    print(f"  Compliance: {data.get('compliance_status')} / {data.get('compliance_reason')}")
    print(f"  Risk: {data.get('risk_status')} ({data.get('risk_score')})")
    print(f"  Plate: {data.get('license_plate')}")
    print(f"  Helmet Model: {data.get('helmet_model')}")
    print(f"  Crowded: {data.get('crowded_scene')}")
    print(f"  AI Review: {data.get('ai_review_recommended')}")
    print(f"  Pedestrians: {data.get('pedestrians', {}).get('count', 0)}")
    print(f"  Image Quality: {data.get('image_quality', {}).get('score')} issues={data.get('image_quality', {}).get('issues', [])}")

    mc_riders = data.get('motorcycle_riders', [])
    print(f"  Motorcycle Riders: {len(mc_riders)}")
    for mr in mc_riders:
        print(f"    MC={mr['motorcycle_id']} riders={mr['rider_count']} occ={mr['occupancy_estimate']} scores={mr.get('assignment_scores', {})}")

    dets = data.get('detections', [])
    persons = [d for d in dets if d['label'] == 'person']
    mcs = [d for d in dets if d['label'] == 'motorcycle']
    print(f"  Detections: {len(dets)} total, {len(persons)} persons, {len(mcs)} motorcycles")
    for d in dets[:15]:
        print(f"    {d['instance_id']}: {d['label']} conf={d['confidence']:.3f} bbox={d['bbox']}")

    print(f"  Violations ({len(data.get('violations', []))}):")
    for v in data.get('violations', []):
        print(f"    {v['type']} conf={v['confidence']} band={v['confidence_band']} "
              f"review={v['human_review_status']} priority={v.get('officer_priority')} "
              f"helmet_reason={v.get('helmet_reason', 'N/A')}")
