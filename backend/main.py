import os, uuid
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np

from utils.image_processing import enhance_image
from ai.locate_anything import LocateAnythingDetector
from ai.helmet_detector import check_helmet_violation
from ai.triple_riding import check_triple_riding
from ai.wrong_side_detector import check_wrong_side_violation
from ai.rider_association import associate_riders, classify_occupancy
from ai.ocr import LicensePlateReader
from ai.evidence_generator import generate_evidence
from ai.repeat_offender import register_violation, get_top_offenders, search_offender
from ai.hotspot_analytics import get_hotspot_analysis, register_hotspot_violation
from ai.forecast_engine import get_predictions, get_tomorrow_forecast, generate_forecast
from ai.report_generator import generate_report, list_reports
from ai.risk_scoring import compute_enhanced_risk, get_risk_status
from database.db import (
    init_db, insert_violation, get_all_violations,
    get_statistics, get_violations_by_type, get_violations_by_day,
    get_top_repeat_offenders, get_monthly_trend, get_recent_violations,
    get_violations_by_hour, get_violations_by_location,
)
from database.models import ViolationRecord
import config

FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"

# ————— Confidence Labels (Standardized) —————
def _confidence_label(band):
    return {
        'high': 'HIGH CONFIDENCE',
        'medium': 'MEDIUM CONFIDENCE',
        'low': 'LOW CONFIDENCE',
        'very_low': 'LOW CONFIDENCE',
    }.get(band, 'LOW CONFIDENCE')

def _reliability_label(band, crowded=False):
    if band == 'high' and not crowded:
        return {'label': 'High', 'reason': 'Clear detection with strong confidence.', 'color': 'bg-green-500/20 text-green-300'}
    if band == 'medium' and not crowded:
        return {'label': 'Medium', 'reason': 'Moderate detection confidence.', 'color': 'bg-yellow-500/20 text-yellow-300'}
    if crowded:
        return {'label': 'Limited', 'reason': 'Crowded scene with multiple overlapping occupants.', 'color': 'bg-orange-500/20 text-orange-300'}
    return {'label': 'Low', 'reason': 'Low detection confidence. Human verification recommended.', 'color': 'bg-red-500/20 text-red-300'}

def _helmet_compliance(v):
    """Analyze helmet detection result with confidence-based reporting."""
    hstate = v.get('helmet_state', '')
    hconf = v.get('helmet_confidence', v.get('confidence', 0))
    if hstate in ('HELMET_PRESENT', 'HELMET_UNKNOWN'):
        return None
    if hstate == 'NO_HELMET':
        band = 'high' if hconf >= 0.8 else ('medium' if hconf >= 0.6 else 'low')
        return {
            'status': f'{_confidence_label(band)} — No Helmet',
            'confidence_band': band,
            'needs_review': band in ('low',) or v.get('needs_review', False),
        }
    return None

# ————— Human Review Status —————
def _review_status(v):
    c = v.get('confidence', 0)
    needs = v.get('needs_review', False)
    crowd = v.get('crowded_scene', False)
    if c >= 0.80 and not needs and not crowd:
        return 'auto_confirmed'
    if c >= 0.60 and not crowd:
        return 'human_review_recommended'
    return 'manual_verification_required'

# ————— Enforcement Recommendations —————
ENFORCEMENT_RECS = {
    'NO_HELMET': {
        'action': 'Suggested Enforcement Response: Issue advisory notice for helmet non-compliance. Recommend follow-up verification at next checkpoint.',
        'escalation': 'Monitor repeat violations. Officer follow-up recommended for persistent offenders.',
    },
    'TRIPLE_RIDING': {
        'action': 'Suggested Enforcement Response: On-site assessment recommended. Document occupancy for records.',
        'escalation': 'School zone: notify traffic education unit. Repeat violations: schedule enforcement drive.',
    },
    'MOTORCYCLE_OVERLOADING': {
        'action': 'Suggested Enforcement Response: Document overloading with evidence. Officer review before further action.',
        'escalation': 'Commercial vehicle: notify transport authority. Repeat: schedule vehicle inspection.',
    },
    'MOTORCYCLE_EXTREME_OVERLOADING': {
        'action': 'Suggested Enforcement Response: Priority review recommended. Document all occupants. Public safety concern.',
        'escalation': 'Coordinate with traffic enforcement unit for vehicle inspection review.',
    },
    'WRONG_SIDE_DRIVING': {
        'action': 'Suggested Enforcement Response: Verify at observed entry point. Consider barrier assessment.',
        'escalation': 'Repeat location: coordinate with traffic engineering for infrastructure review.',
    },
}

# ————— Occupancy Estimate —————
def _occupancy_estimate(rider_count, conf):
    if rider_count <= 2:
        return f'{rider_count} occupant{"s" if rider_count != 1 else ""}'
    if rider_count == 3:
        return '3 occupants'
    if rider_count == 4:
        return '4-5 occupants'
    if rider_count >= 5:
        return '5+ occupants'
    return f'{rider_count} occupants'

# ————— Explainable Reason —————
def _build_explainable_reason(violation_type, details):
    prefix = _confidence_label(details.get('confidence_band', 'medium'))
    occ_est = _occupancy_estimate(details.get('rider_count', 0), details.get('confidence', 0))
    reasons = {
        'NO_HELMET': f"{prefix} — No Helmet. Rider detected without protective headgear. {details.get('helmet_state', 'Helmet detection analysis completed.')}",
        'TRIPLE_RIDING': f"{prefix} — Triple Riding. {occ_est} associated with a single motorcycle.",
        'MOTORCYCLE_OVERLOADING': f"{prefix} — Motorcycle Overloading. {occ_est} detected — exceeds legal occupant limit.",
        'MOTORCYCLE_EXTREME_OVERLOADING': f"{prefix} — Extreme Overloading. {occ_est} — immediate enforcement recommended.",
        'WRONG_SIDE_DRIVING': f"{prefix} — Wrong-Side Driving. Vehicle detected traveling against designated traffic flow.",
    }
    reason = reasons.get(violation_type, f'{prefix} — traffic violation detected.')
    status = _review_status(details)
    if status == 'manual_verification_required':
        reason += ' Manual verification required before enforcement action.'
    elif status == 'human_review_recommended':
        reason += ' Human review recommended before enforcement action.'
    return reason


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    os.makedirs(config.EVIDENCE_DIR, exist_ok=True)
    os.makedirs(config.REPORT_DIR, exist_ok=True)
    yield

app = FastAPI(title="TRINETRA AI — Traffic Enforcement Intelligence Platform", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "operational", "service": "TRINETRA AI — Traffic Enforcement Intelligence", "version": "3.0.0"}


@app.post("/api/detect")
async def detect_violations(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(400, "Failed to decode image")

    filename = f"{uuid.uuid4().hex}_{file.filename}"
    filepath = os.path.join(config.UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    processed = enhance_image(image)
    detector = LocateAnythingDetector()
    raw_detections = detector.detect(processed)

    # Filter low-confidence vehicles
    filtered = []
    for d in raw_detections:
        if d['class_id'] in (2, 3, 5, 7) and d['confidence'] < config.VEHICLE_CONFIDENCE_THRESHOLD:
            continue
        filtered.append(d)

    instance_counts = {}
    detections = []
    for d in filtered:
        label = d['label']
        instance_counts[label] = instance_counts.get(label, 0) + 1
        d['instance_id'] = f"{label}_{instance_counts[label]}"
        detections.append(d)

    # Crowded scene detection (compute before violation loop)
    person_count = len([d for d in detections if d['label'] == 'person'])
    motorcycle_count = len([d for d in detections if d['label'] == 'motorcycle'])
    crowded_scene = person_count >= 6 or (person_count >= 4 and motorcycle_count >= 2)

    # Detect violations (seatbelt disabled — removed from pipeline)
    violations = []
    for fn in [check_helmet_violation, check_triple_riding, check_wrong_side_violation]:
        for v in fn(detections, processed):
            v['confidence_band'] = v.get('confidence_band', 'medium')
            v['occupancy_estimate'] = _occupancy_estimate(v.get('rider_count', 0), v.get('confidence', 0))
            v['human_review_status'] = _review_status(v)
            rec = ENFORCEMENT_RECS.get(v["violation_type"], {})
            v['enforcement_recommendation'] = rec.get('action', 'Standard enforcement procedure.')
            v['escalation'] = rec.get('escalation', '')
            v['reliability_badge'] = _reliability_label(v['confidence_band'], crowded_scene)
            hc = _helmet_compliance(v)
            v['helmet_compliance'] = hc
            violations.append(v)

    # License Plate OCR
    plate_text, plate_conf = "", 0.0
    vehicles = [d for d in detections if d['class_id'] in (2, 3, 5, 7)]
    if vehicles:
        reader = LicensePlateReader()
        biggest = max(vehicles, key=lambda v:
            (v["bbox"][2] - v["bbox"][0]) * (v["bbox"][3] - v["bbox"][1]))
        plate_text, plate_conf = reader.read_plate(processed, biggest["bbox"])

    vehicle_type = next(
        (config.VEHICLE_CLASSES[d["class_id"]] for d in detections
         if d["class_id"] in config.VEHICLE_CLASSES), "")

    # Rider association
    persons_mc = [d for d in detections if d['label'] == 'person']
    motorcycles = [d for d in detections if d['label'] == 'motorcycle']
    mc_associations = associate_riders(persons_mc, motorcycles, processed.shape[:2])
    motorcycle_riders = []
    any_needs_review = False
    for assoc in mc_associations:
        mc = assoc['motorcycle']
        riders = assoc['riders']
        occ = assoc.get('rider_count', 0)
        occ_est = _occupancy_estimate(occ, 0.5)
        motorcycle_riders.append({
            'motorcycle_id': mc['instance_id'],
            'motorcycle_bbox': [round(v, 1) for v in mc['bbox']],
            'rider_count': occ,
            'occupancy_estimate': occ_est,
            'confirmed_count': assoc.get('confirmed_count', occ),
            'possible_count': assoc.get('possible_count', 0),
            'riders': [r['instance_id'] for r in riders],
            'assignment_scores': assoc.get('assignment_scores', {}),
        })
        if occ >= 4 or crowded_scene:
            any_needs_review = True

    evidence_path = generate_evidence(processed, detections, violations, (plate_text, plate_conf))

    total_risk = sum(v.get('severity_score', config.RISK_SCORES.get(v["violation_type"], 0)) for v in violations)
    risk_status = 'NONE'
    if total_risk > 0:
        risk_status = 'MODERATE' if total_risk < 75 else ('HIGH' if total_risk < 120 else 'CRITICAL')

    location_hint = ''
    for v in violations:
        record = ViolationRecord(
            vehicle_number=plate_text,
            vehicle_type=vehicle_type,
            violation_type=v["violation_type"],
            confidence=v["confidence"],
            image_path=filepath,
            evidence_path=evidence_path,
            location=location_hint,
            timestamp=datetime.now().isoformat(),
        )
        insert_violation(record)
        if plate_text:
            register_violation(plate_text, v["violation_type"], datetime.now().isoformat())
        register_hotspot_violation(v["violation_type"], location_hint)

    ai_review_needed = any(v.get('needs_review', False) for v in violations) or any_needs_review or crowded_scene

    return {
        "success": True,
        "detections": [
            {"instance_id": d["instance_id"], "label": d["label"],
             "confidence": round(d["confidence"], 3),
             "bbox": [round(v, 1) for v in d["bbox"]]}
            for d in detections
        ],
        "motorcycle_riders": motorcycle_riders,
        "violations": [
            {
                "type": v["violation_type"],
                "confidence": round(v["confidence"], 3),
                "confidence_band": v.get("confidence_band", "medium"),
                "confidence_label": _confidence_label(v.get("confidence_band", "medium")),
                "description": v.get("description", ""),
                "occupancy_estimate": v["occupancy_estimate"],
                "explainable_reason": _build_explainable_reason(v["violation_type"], v),
                "human_review_status": v["human_review_status"],
                "enforcement_recommendation": v["enforcement_recommendation"],
                "escalation": v.get("escalation", ""),
                "reliability_badge": v["reliability_badge"],
                "helmet_compliance": v.get("helmet_compliance"),
                "involved_objects": v.get("involved_objects", []),
                "severity_score": v.get("severity_score", config.RISK_SCORES.get(v["violation_type"], 0)),
                "needs_review": v.get("needs_review", False),
            }
            for v in violations
        ],
        "risk_score": total_risk,
        "risk_status": risk_status,
        "crowded_scene": crowded_scene,
        "ai_review_recommended": ai_review_needed,
        "operational_intelligence": {
            "mode": "Traffic Enforcement Intelligence Center",
            "note": "All violations include confidence-based reporting, explainable AI reasoning, human review status, and enforcement recommendations."
        },
        "license_plate": {"number": plate_text, "confidence": round(plate_conf, 3)} if plate_text else None,
        "evidence_path": os.path.basename(evidence_path) if evidence_path else None,
    }


@app.get("/api/violations")
def list_violations(
    vehicle_number: str = Query(None),
    violation_type: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
    location: str = Query(None),
    limit: int = Query(100),
):
    violations_list = get_all_violations(
        vehicle_number=vehicle_number,
        violation_type=violation_type,
        date_from=date_from,
        date_to=date_to,
        location=location,
    )
    return {"total": len(violations_list), "violations": [v.to_dict() for v in violations_list[:limit]]}


@app.get("/api/violations/recent")
def recent_violations(limit: int = Query(10)):
    return {"violations": [v.to_dict() for v in get_recent_violations(limit)]}


@app.get("/api/violations/stats")
def violation_stats():
    return get_statistics()


@app.get("/api/violations/analytics")
def violation_analytics():
    return {
        "by_type": get_violations_by_type(),
        "by_day": get_violations_by_day(),
        "by_hour": get_violations_by_hour(),
        "by_location": get_violations_by_location(),
        "repeat_offenders": get_top_repeat_offenders(),
        "monthly_trend": get_monthly_trend(),
    }


@app.get("/api/evidence/{filename}")
def get_evidence(filename: str):
    filepath = os.path.join(config.EVIDENCE_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Evidence not found")
    return FileResponse(filepath, media_type="image/jpeg")


# ——————— Repeat Offender Intelligence ———————

@app.get("/api/intelligence/repeat-offenders")
def repeat_offenders(limit: int = Query(20), risk_status: str = Query(None)):
    offenders = get_top_offenders(limit=limit, risk_status=risk_status)
    return {"offenders": offenders, "total": len(offenders)}


@app.get("/api/intelligence/repeat-offenders/search")
def search_repeat_offender(vehicle: str = Query(...)):
    return {"offenders": search_offender(vehicle)}


# ——————— Violation Hotspot Analytics ———————

@app.get("/api/intelligence/hotspots")
def violation_hotspots():
    return get_hotspot_analysis()


# ——————— Predictive Enforcement ———————

@app.get("/api/intelligence/forecasts")
def violation_forecasts():
    forecasts = get_predictions()
    return {"forecasts": forecasts, "total": len(forecasts)}


@app.get("/api/intelligence/forecasts/tomorrow")
def tomorrow_forecast():
    tomorrow_f = get_tomorrow_forecast()
    if not tomorrow_f:
        tomorrow_f = [f for f in generate_forecast() if f.get('forecast_date', '').startswith((datetime.now().replace(hour=0, minute=0, second=0) + __import__('datetime').timedelta(days=1)).date().isoformat())]
    return {"forecasts": tomorrow_f}


# ——————— Report Generation ———————

@app.post("/api/intelligence/reports/generate")
def generate_new_report(report_type: str = Query("daily")):
    if report_type not in ("daily", "weekly", "monthly"):
        raise HTTPException(400, "report_type must be daily, weekly, or monthly")
    result = generate_report(report_type)
    return {"success": True, "report": result}


@app.get("/api/intelligence/reports")
def list_all_reports():
    return {"reports": list_reports()}


@app.get("/api/intelligence/reports/{report_id}")
def download_report(report_id: int):
    from database.db import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports WHERE id=?", (report_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Report not found")
    filepath = row['file_path']
    if not os.path.exists(filepath):
        raise HTTPException(404, "Report file not found")
    return FileResponse(filepath, media_type="application/pdf",
                        filename=os.path.basename(filepath))


# ——————— AI Copilot ———————

@app.get("/api/copilot/query")
def copilot_query(q: str = Query(...)):
    from ai.copilot_engine import answer_query
    return {"query": q, "answer": answer_query(q)}


# ——————— Enforcement Dashboard ———————

@app.get("/api/intelligence/dashboard")
def enforcement_dashboard():
    from database.db import get_statistics
    stats = get_statistics()
    hotspots = get_hotspot_analysis()
    forecasts = get_predictions()[:5]
    offenders = get_top_offenders(limit=10)
    return {
        "stats": stats,
        "hotspots": hotspots,
        "forecasts": forecasts,
        "top_offenders": offenders,
    }


# ——————— Executive Summary ———————

@app.get("/api/intelligence/executive-summary")
def executive_summary():
    from database.db import get_statistics, get_all_violations
    from datetime import datetime, timedelta
    stats = get_statistics()
    hotspots = get_hotspot_analysis()
    offenders = get_top_offenders(limit=5)
    forecasts = get_predictions()[:3]
    today_str = datetime.now().date().isoformat()
    today_violations = get_all_violations(date_from=today_str)
    violations_by_type = get_violations_by_type()

    violation_types_count = len(violations_by_type) if violations_by_type else 0
    top_type = violations_by_type[0] if violations_by_type else None
    total_risk = sum(o.get('risk_score', 0) for o in offenders)
    avg_risk = round(total_risk / len(offenders), 1) if offenders else 0

    return {
        "total_violations": stats.get('total', 0),
        "unique_vehicles": stats.get('unique_vehicles', 0),
        "high_risk_offenders": stats.get('high_risk_offenders', 0),
        "today_violations": len(today_violations),
        "active_hotspots": len(hotspots.get('hotspots', [])),
        "active_forecasts": len(forecasts),
        "top_violation_type": top_type['type'] if top_type else None,
        "top_violation_count": top_type['count'] if top_type else 0,
        "top_offender": offenders[0]['vehicle_number'] if offenders else None,
        "top_offender_count": offenders[0]['total_violations'] if offenders else 0,
        "average_risk_score": avg_risk,
        "top_location": hotspots.get('by_location', [{}])[0].get('location', 'N/A') if hotspots.get('by_location') else 'N/A',
    }


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
