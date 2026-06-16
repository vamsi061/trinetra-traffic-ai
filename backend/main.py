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
from ai.detector import ObjectDetector
from ai.helmet_detector import check_helmet_violation
from ai.triple_riding import check_triple_riding
from ai.seatbelt_detector import check_seatbelt_violation
from ai.wrong_side_detector import check_wrong_side_violation
from ai.ocr import LicensePlateReader
from ai.evidence_generator import generate_evidence
from database.db import (
    init_db, insert_violation, get_all_violations,
    get_statistics, get_violations_by_type, get_violations_by_day,
    get_top_repeat_offenders, get_monthly_trend, get_recent_violations,
)
from database.models import ViolationRecord
import config

FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    os.makedirs(config.EVIDENCE_DIR, exist_ok=True)
    yield

app = FastAPI(title="TRINETRA AI API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "operational", "service": "TRINETRA AI", "version": "2.0.0"}

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
    detector = ObjectDetector()
    detections = detector.detect(processed)

    violations = []
    for fn in [check_helmet_violation, check_triple_riding,
               check_seatbelt_violation, check_wrong_side_violation]:
        args = [detections, processed] if fn in [check_helmet_violation, check_seatbelt_violation, check_wrong_side_violation] else [detections]
        for v in fn(*args):
            violations.append(v)

    plate_text, plate_conf = "", 0.0
    vehicles = detector.filter_vehicles(detections)
    if vehicles:
        reader = LicensePlateReader()
        biggest = max(vehicles, key=lambda v:
            (v["bbox"][2] - v["bbox"][0]) * (v["bbox"][3] - v["bbox"][1]))
        plate_text, plate_conf = reader.read_plate(processed, biggest["bbox"])

    vehicle_type = next(
        (config.VEHICLE_CLASSES[d["class_id"]] for d in detections
         if d["class_id"] in config.VEHICLE_CLASSES), "")

    evidence_path = generate_evidence(processed, detections, violations,
                                       (plate_text, plate_conf))

    for v in violations:
        record = ViolationRecord(
            vehicle_number=plate_text,
            vehicle_type=vehicle_type,
            violation_type=v["violation_type"],
            confidence=v["confidence"],
            image_path=filepath,
            evidence_path=evidence_path,
            timestamp=datetime.now().isoformat(),
        )
        insert_violation(record)

    return {
        "success": True,
        "detections": [
            {"label": d["label"], "confidence": round(d["confidence"], 3),
             "bbox": [round(v, 1) for v in d["bbox"]]}
            for d in detections
        ],
        "violations": [
            {"type": v["violation_type"], "confidence": round(v["confidence"], 3),
             "description": v.get("description", "")}
            for v in violations
        ],
        "license_plate": {"number": plate_text, "confidence": round(plate_conf, 3)} if plate_text else None,
        "evidence_path": os.path.basename(evidence_path) if evidence_path else None,
    }

@app.get("/api/violations")
def list_violations(
    vehicle_number: str = Query(None),
    violation_type: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
    limit: int = Query(100),
):
    violations = get_all_violations(
        vehicle_number=vehicle_number,
        violation_type=violation_type,
        date_from=date_from,
        date_to=date_to,
    )
    return {"total": len(violations), "violations": [v.to_dict() for v in violations[:limit]]}

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
        "repeat_offenders": get_top_repeat_offenders(),
        "monthly_trend": get_monthly_trend(),
    }

@app.get("/api/evidence/{filename}")
def get_evidence(filename: str):
    filepath = os.path.join(config.EVIDENCE_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Evidence not found")
    return FileResponse(filepath, media_type="image/jpeg")

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
