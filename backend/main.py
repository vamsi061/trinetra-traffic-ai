import os, uuid
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np

from utils.image_processing import enhance_image
from ai.locate_anything import LocateAnythingDetector
from ai.helmet_detector import check_helmet_violation
from ai.triple_riding import check_triple_riding
from ai.quality_assessment import assess_quality
from ai.parking_detector import check_illegal_parking
from ai.evidence_package import generate_evidence_report

from ai.rider_association import associate_riders, classify_occupancy
from ai.helmet_detector import get_helmet_service, HELMET_STATE_PRESENT, HELMET_STATE_ABSENT, HELMET_STATE_UNKNOWN
from ai.ocr import LicensePlateReader
from ai.evidence_generator import generate_evidence
from ai.repeat_offender import register_violation, get_top_offenders, search_offender
from ai.hotspot_analytics import get_hotspot_analysis, register_hotspot_violation
from ai.forecast_engine import get_predictions, get_tomorrow_forecast, generate_forecast
from ai.report_generator import generate_report, list_reports
from ai.risk_scoring import compute_enhanced_risk, get_risk_status
from ai.vehicle_risk import compute_vehicle_risk_profile
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
    if band == 'low':
        return {'label': 'Low', 'reason': 'Low detection confidence. Human verification recommended.', 'color': 'bg-red-500/20 text-red-300'}
    return {'label': 'Low', 'reason': 'Poor visibility or occlusion. Verification required.', 'color': 'bg-red-500/20 text-red-300'}

def _helmet_compliance(v):
    """Analyze helmet detection result with confidence-based reporting."""
    hstate = v.get('helmet_state', '')
    hconf = v.get('helmet_confidence', v.get('confidence', 0))
    if hstate == 'HELMET_PRESENT':
        return None
    if hstate == 'NO_HELMET':
        band = 'high' if hconf >= 0.8 else ('medium' if hconf >= 0.6 else 'low')
        label_map = {
            'high': 'Probable Helmet Non-Compliance',
            'medium': 'Possible Helmet Non-Compliance',
            'low': 'Possible Helmet Non-Compliance',
        }
        return {
            'status': f'{label_map.get(band, "Possible Helmet Non-Compliance")}',
            'confidence_band': band,
            'needs_review': band in ('low',) or v.get('needs_review', False),
        }
    if hstate == 'HELMET_UNKNOWN':
        # Uncertain detection — possible non-compliance with verification
        return {
            'status': 'Possible Helmet Non-Compliance',
            'confidence_band': 'low',
            'needs_review': True,
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
        'action': 'Officer Review Recommended: Advisory notice for helmet non-compliance. Consider follow-up verification at next checkpoint.',
        'escalation': 'Monitor repeat cases. Officer follow-up recommended for persistent offenders.',
    },
    'TRIPLE_RIDING': {
        'action': 'Officer Review Recommended: On-site assessment. Document occupancy for records.',
        'escalation': 'School zone: notify traffic education unit. Repeat cases: schedule enforcement drive.',
    },
    'MOTORCYCLE_OVERLOADING': {
        'action': 'Additional Evidence Suggested: Document overloading with evidence. Officer review before further action.',
        'escalation': 'Commercial vehicle: notify transport authority. Repeat: schedule vehicle inspection.',
    },
    'MOTORCYCLE_EXTREME_OVERLOADING': {
        'action': 'Vehicle Inspection Recommended: Priority review. Document all occupants. Public safety concern.',
        'escalation': 'Coordinate with traffic enforcement unit for vehicle inspection review.',
    },
}

# ————— Occupancy Estimate —————
def _occupancy_estimate(rider_count, conf, single_motorcycle=False):
    # Sanity: single motorcycle with ≤3 visible riders → cap at "3 occupants"
    if single_motorcycle and rider_count <= 3 and rider_count > 0:
        return '3 occupants' if rider_count == 3 else f'{rider_count} occupant{"s" if rider_count != 1 else ""}'
    if conf >= 0.80:
        if rider_count <= 0:
            return 'No occupants detected'
        if rider_count <= 2:
            return f'{rider_count} occupant{"s" if rider_count != 1 else ""}'
        if rider_count == 3:
            return '3 occupants'
        if rider_count <= 5:
            return '4-5 occupants'
        if rider_count <= 8:
            return '6-8 occupants'
        return '10-12 occupants'
    if rider_count <= 0:
        return 'Occupants uncertain'
    if rider_count <= 2:
        return '1-2 occupants'
    if rider_count <= 3:
        return '2-3 occupants'
    if rider_count <= 5:
        return '4-5 occupants'
    if rider_count <= 8:
        return '6-8 occupants'
    return '10-12 occupants'

# ————— Explainable Reason —————
def _build_explainable_reason(violation_type, details):
    prefix = _confidence_label(details.get('confidence_band', 'medium'))
    occ_est = _occupancy_estimate(details.get('rider_count', 0), details.get('confidence', 0))
    hc = details.get('helmet_compliance')
    helmet_desc = hc['status'] if hc else ''
    helmet_state = details.get('helmet_state', '')
    confidence_pct = f"{details.get('confidence', 0) * 100:.0f}%"
    review_map = {
        'auto_confirmed': 'Automatically confirmed — no further review required.',
        'human_review_recommended': 'Human review recommended before enforcement action.',
        'manual_verification_required': 'Manual verification required — insufficient confidence for automated decision.',
    }
    review_note = review_map.get(details.get('human_review_status', ''), '')

    if violation_type == 'NO_HELMET':
        if helmet_state == 'HELMET_UNKNOWN':
            reason = f"{prefix} — {helmet_desc}. Head region partially visible but no clear helmet features detected. Confidence: {confidence_pct}. {review_note}"
        else:
            reason = f"{prefix} — {helmet_desc}. Rider head region clearly visible and no protective headgear detected. Evidence: direct visual observation of head region. Confidence: {confidence_pct}. {review_note}"
    elif violation_type == 'TRIPLE_RIDING':
        reason = f"{prefix} — Triple riding detected. {occ_est} associated with a single motorcycle. Evidence: multiple persons aligned with motorcycle seating positions. Confidence: {confidence_pct}. {review_note}"
    elif violation_type == 'MOTORCYCLE_OVERLOADING':
        reason = f"{prefix} — Motorcycle overloading. {occ_est} exceeds legal occupant limit. Evidence: multiple distinct riders associated with motorcycle. Confidence: {confidence_pct}. {review_note}"
    elif violation_type == 'MOTORCYCLE_EXTREME_OVERLOADING':
        reason = f"{prefix} — Extreme overloading. {occ_est} — public safety concern. Evidence: excessive number of persons on single motorcycle. Confidence: {confidence_pct}. {review_note}"
    elif violation_type == 'POSSIBLE_ILLEGAL_PARKING':
        reason = f"{prefix} — Possible illegal parking detected. Vehicle positioned in restricted zone. Evidence: spatial analysis of vehicle position relative to roadway features. {review_note}"
    else:
        reason = f"{prefix} — traffic violation detected. Confidence: {confidence_pct}. {review_note}"
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

    # ————— Violation Detection Loop —————
    violations = []
    for fn in [check_helmet_violation, check_triple_riding]:
        for v in fn(detections, processed if fn is check_triple_riding else image):
            # FIX: Skip NORMAL (non-violation) entries from triple_riding
            if v['violation_type'] == 'NORMAL':
                continue
            v['confidence_band'] = v.get('confidence_band', 'medium')
            is_single_mc = len([d for d in detections if d['label'] == 'motorcycle']) == 1
            v['occupancy_estimate'] = _occupancy_estimate(v.get('rider_count', 0), v.get('confidence', 0), single_motorcycle=is_single_mc)
            v['human_review_status'] = _review_status(v)
            rec = ENFORCEMENT_RECS.get(v["violation_type"], {})
            v['enforcement_recommendation'] = rec.get('action', 'Standard enforcement procedure.')
            v['escalation'] = rec.get('escalation', '')
            v['reliability_badge'] = _reliability_label(v['confidence_band'], crowded_scene)
            hc = _helmet_compliance(v)
            v['helmet_compliance'] = hc
            # Officer Priority
            sev = v.get('severity_score', config.RISK_SCORES.get(v["violation_type"], 0))
            if sev >= 95:
                v['officer_priority'] = 'URGENT REVIEW'
            elif sev >= 75:
                v['officer_priority'] = 'HIGH PRIORITY'
            elif sev >= 30:
                v['officer_priority'] = 'MEDIUM PRIORITY'
            else:
                v['officer_priority'] = 'LOW PRIORITY'
            violations.append(v)

    # ————— Compliance Assessment (FINAL decision) —————
    # A vehicle can only be COMPLIANT if no violations are detected.
    ALL_VIOLATION_TYPES = (
        'NO_HELMET', 'TRIPLE_RIDING', 'MOTORCYCLE_OVERLOADING',
        'MOTORCYCLE_EXTREME_OVERLOADING', 'POSSIBLE_ILLEGAL_PARKING',
    )
    has_actual_violations = any(
        vt in ALL_VIOLATION_TYPES
        for vt in [v['violation_type'] for v in violations]
    )
    if not has_actual_violations:
        motorcycles_check = any(d['label'] == 'motorcycle' for d in detections)
        persons_check = any(d['label'] == 'person' for d in detections)
        if motorcycles_check and persons_check:
            compliance_status = 'COMPLIANT'
            compliance_reason = 'All observed vehicles appear compliant with traffic regulations.'
        else:
            # No motorcycle, or motorcycle without visible rider — insufficient data
            compliance_status = 'NONE'
            compliance_reason = ''
    else:
        compliance_status = 'NONE'
        compliance_reason = ''

    # ————— License Plate OCR —————
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
    is_single_mc = len(motorcycles) == 1
    for assoc in mc_associations:
        mc = assoc['motorcycle']
        riders = assoc['riders']
        occ = assoc.get('rider_count', 0)
        occ_est = _occupancy_estimate(occ, 0.5, single_motorcycle=is_single_mc)
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

    evidence_path = generate_evidence(processed, detections, violations, (plate_text, plate_conf), source_filename=file.filename)

    # Image Quality Assessment
    quality = assess_quality(image)

    # Illegal Parking Detection — skip if vehicle is moving (mounted rider in travel lane)
    has_mc = any(d['label'] == 'motorcycle' for d in detections)
    has_person = any(d['label'] == 'person' for d in detections)
    has_mounted_rider = has_mc and has_person and any(mr.get('rider_count', 0) > 0 for mr in motorcycle_riders)
    is_moving_hint = has_mounted_rider or (not has_actual_violations and has_mc)
    parking_violations = check_illegal_parking(detections, image.shape, moving_vehicle_hint=is_moving_hint)
    for v in parking_violations:
        v['confidence_band'] = v.get('confidence_band', 'low')
        v['occupancy_estimate'] = 'N/A'
        v['human_review_status'] = 'manual_verification_required'
        rec = ENFORCEMENT_RECS.get(v["violation_type"], {})
        v['enforcement_recommendation'] = rec.get('action', 'Officer Review Recommended: Assess parking violation on-site.')
        v['escalation'] = rec.get('escalation', '')
        v['reliability_badge'] = _reliability_label(v['confidence_band'], crowded_scene)
        v['helmet_compliance'] = None
        v['confidence_label'] = _confidence_label(v.get('confidence_band', 'low'))
        v['officer_priority'] = 'MEDIUM PRIORITY'
    # Only add parking violations if no compliance override
    if compliance_status != 'COMPLIANT':
        violations.extend(parking_violations)

    # Pedestrian stats
    person_detections = [d for d in detections if d['label'] == 'person']
    pedestrian_count = len(person_detections)

    # Plate visibility score
    plate_visibility = 'High'
    if plate_text:
        plate_visibility = 'High'
        if quality.get('score') in ('Fair', 'Poor'):
            plate_visibility = 'Medium' if quality['score'] == 'Fair' else 'Low'
        if plate_conf < 0.6:
            plate_visibility = 'Low'
        elif plate_conf < 0.8:
            plate_visibility = 'Medium' if plate_visibility == 'High' else 'Low'

    # FIX 4+5: Risk score — compliant vehicles get 0-10 LOW
    if compliance_status == 'COMPLIANT':
        total_risk = 0
        risk_status = 'LOW'
    else:
        actual_violations = [v for v in violations
                            if v['violation_type'] not in ('NORMAL',)]
        total_risk = min(sum(
            v.get('severity_score', config.RISK_SCORES.get(v["violation_type"], 0))
            for v in actual_violations
        ), 100)
        risk_status = 'NONE'
        if total_risk > 0:
            risk_status = 'LOW' if total_risk <= 25 else ('MODERATE' if total_risk <= 50 else ('HIGH' if total_risk <= 75 else 'CRITICAL'))

    location_hint = ''
    for v in violations:
        # Skip NORMAL/compliant entries in database
        if v.get('violation_type') == 'NORMAL':
            continue
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

    # Generate evidence report
    license_plate_dict = {"number": plate_text, "confidence": round(plate_conf, 3), "visibility": plate_visibility} if plate_text else None
    evidence_report_path = generate_evidence_report(
        filepath, detections, violations,
        license_plate_dict, quality, total_risk, risk_status,
        source_filename=file.filename
    )

    # Filter violations for response: skip NORMAL entries
    response_violations = [v for v in violations if v['violation_type'] not in ('NORMAL',)]

    # FIX 6: Reliability — HIGH for clear single-rider helmet-visible images
    if compliance_status == 'COMPLIANT' and not crowded_scene and quality.get('score') in ('Excellent', 'Good'):
        reliability_override = {'label': 'High', 'reason': 'Clear detection with strong confidence.', 'color': 'bg-green-500/20 text-green-300'}
    else:
        reliability_override = None

    # Helmet model diagnostics
    helmet_service = get_helmet_service()
    helmet_model_info = helmet_service.get_model_info()

    return {
        "success": True,
        "detections": [
            {"instance_id": d["instance_id"], "label": d["label"],
             "confidence": round(d["confidence"], 3),
             "bbox": [round(v, 1) for v in d["bbox"]]}
            for d in detections
        ],
        "pedestrians": {
            "count": pedestrian_count,
            "detected": [{"instance_id": d["instance_id"], "bbox": [round(v, 1) for v in d["bbox"]],
                          "confidence": round(d["confidence"], 3)} for d in person_detections],
        },
        "image_quality": quality,
        "motorcycle_riders": motorcycle_riders,
        "compliance_status": compliance_status,
        "compliance_reason": compliance_reason,
        "helmet_model": helmet_model_info,
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
                "reliability_badge": reliability_override if (compliance_status == 'COMPLIANT' and reliability_override) else v["reliability_badge"],
                "helmet_compliance": v.get("helmet_compliance"),
                "helmet_reason": v.get("helmet_reason", ""),
                "involved_objects": v.get("involved_objects", []),
                "severity_score": v.get("severity_score", config.RISK_SCORES.get(v["violation_type"], 0)),
                "needs_review": v.get("needs_review", False),
                "officer_priority": v.get("officer_priority", "MEDIUM PRIORITY"),
            }
            for v in response_violations
        ],
        "risk_score": total_risk,
        "risk_status": risk_status,
        "crowded_scene": crowded_scene,
        "helmet_non_compliance_count": len([v for v in response_violations if v["violation_type"] == "NO_HELMET"]),
        "ai_review_recommended": ai_review_needed,
        "operational_intelligence": {
            "mode": "Traffic Enforcement Intelligence Center",
            "note": "All violations include confidence-based reporting, explainable AI reasoning, human review status, and enforcement recommendations."
        },
        "license_plate": {"number": plate_text, "confidence": round(plate_conf, 3), "visibility": plate_visibility} if plate_text else None,
        "evidence_path": os.path.basename(evidence_path) if evidence_path else None,
        "evidence_report": os.path.basename(evidence_report_path) if evidence_report_path else None,
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


@app.get("/api/evidence/report/{filename}")
def get_evidence_report(filename: str):
    filepath = os.path.join(config.REPORT_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Report not found")
    media = "application/pdf" if filename.endswith('.pdf') else "text/html"
    return FileResponse(filepath, media_type=media)


# ——————— Vehicle Risk Profile ———————

@app.get("/api/intelligence/vehicle-risk/{vehicle_number}")
def vehicle_risk_profile(vehicle_number: str):
    from database.db import get_all_violations
    all_v = get_all_violations(vehicle_number=vehicle_number)
    profile = compute_vehicle_risk_profile(vehicle_number, all_v)
    return profile


# ——————— Vehicle Watchlist ———————

@app.get("/api/intelligence/watchlist")
def vehicle_watchlist():
    from database.db import get_all_violations
    all_v = get_all_violations()
    vehicles = set(v.vehicle_number for v in (all_v or []) if v.vehicle_number)
    watchlist = []
    for vnum in vehicles:
        vlist = [v for v in (all_v or []) if v.vehicle_number == vnum]
        profile = compute_vehicle_risk_profile(vnum, vlist)
        if profile['watchlist']:
            watchlist.append(profile)
    watchlist.sort(key=lambda x: x['risk_score'], reverse=True)
    return {"watchlist": watchlist, "total": len(watchlist)}


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

    # Compute overall reliability
    total = stats.get('total', 0)
    all_v = get_all_violations()
    high_conf = sum(1 for v in all_v if getattr(v, 'confidence', 0) >= 0.8) if all_v else 0
    reliability = 'High' if total > 0 and high_conf / total >= 0.7 else ('Medium' if total > 0 and high_conf / total >= 0.4 else 'Low') if total > 0 else 'N/A'

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
        "overall_reliability": reliability,
        "top_location": hotspots.get('by_location', [{}])[0].get('location', 'N/A') if hotspots.get('by_location') else 'N/A',
        "helmet_non_compliance_count": sum(1 for v in all_v if getattr(v, 'violation_type', '') == 'NO_HELMET') if all_v else 0,
    }


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
