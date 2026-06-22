---
title: TRINETRA AI
emoji: 🚦
colorFrom: red
colorTo: blue
sdk: docker
app_port: 7860
---

# TRINETRA AI — Traffic Violation Detection Platform

AI-powered traffic enforcement intelligence platform for smart cities. Automatically detects 8 violation types from traffic camera images, reads license plates, generates evidence PDFs, and provides predictive enforcement analytics.

**Hackathon Alignment**: Developed for the *Automated Photo Identification and Classification for Traffic Violations Using Computer Vision* challenge — covering image preprocessing, vehicle/pedestrian detection, violation detection (helmet, triple riding, overloading, seatbelt, wrong-side, red-light, stop-line, illegal parking), license plate OCR, evidence generation, and performance evaluation (Accuracy, Precision, Recall, F1, mAP).

## Features

- **8 Violation Detectors** — Helmet non-compliance, triple riding, motorcycle overloading, seatbelt non-compliance, wrong-side driving, red-light violation, stop-line violation, illegal parking
- **License Plate OCR** — Full plate text extraction via EasyOCR with fragment recombination & plate enhancement
- **Vehicle & Road User Detection** — YOLOv8s detects cars, motorcycles, buses, trucks, persons, traffic lights, stop signs
- **Explainable AI** — Per-violation confidence, reliability badge, human review status, and enforcement recommendation
- **Risk Scoring** — Enhanced profiling with repeat-offender multipliers, location risk, time-of-day risk
- **Evidence Reports** — Professional PDF reports (fpdf2) with case info, quality assessment, violation table, scene assessment, officer notes
- **Repeat Offender Tracking** — Vehicle-level violation history and risk scoring
- **Hotspot Analytics** — Location-based violation clustering with risk levels
- **Forecast Engine** — Predictive enforcement recommendations based on historical patterns
- **AI Copilot** — Natural-language query engine for intelligence data
- **Enforcement Dashboard** — Smart city decision support with charts & recommendations
- **Image Enhancement** — Handles low light, rain, shadows, motion blur, haze via multi-stage enhancement pipeline
- **Scene Reasoning** — Florence-2 based scene understanding with template fallback
- **Image Quality Assessment** — Brightness, contrast, sharpness, noise metrics with issue detection
- **Performance Evaluation** — 309-image benchmark across 15 categories, automated 15-phase validation pipeline

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- npm

### Run

```bash
bash start.sh
```

Opens at **http://localhost:8000**.

On first run, `start.sh` automatically downloads the required models:
- `yolov8s.pt` (21.5 MB) — supplied by Ultralytics hub
- `helmet_yolov8n.pt` (5.9 MB) — from Hugging Face `iam-tsr/yolov8n-helmet-detection`

### Development Mode (hot reload)

```bash
bash start.sh --dev
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Install Dependencies Only

```bash
bash start.sh --install
```

## Deploy to Hugging Face Spaces (Free)

1. Go to https://huggingface.co/new-space
2. Set **Space Name** to `trinetra-traffic-ai`
3. Select **Docker** as the SDK
4. Choose **CPU basic** (free) as the hardware
5. Click **Create Space**
6. Push code to the Space:
   ```bash
   git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/trinetra-traffic-ai
   git push hf main
   ```

The Space builds and deploys automatically. Visit `https://YOUR_USERNAME-trinetra-traffic-ai.hf.space` to use the app.

## Project Structure

```
├── backend/
│   ├── ai/                      # AI models & detection modules
│   │   ├── detector.py          # YOLOv8s object detection (singleton)
│   │   ├── helmet_detector.py   # YOLO helmet model (v5 crop-based) + HSV fallback
│   │   ├── rider_association.py # Person-motorcycle association scoring
│   │   ├── triple_riding.py     # Occupancy analysis & overloading classification
│   │   ├── seatbelt_detector.py # Car occupant seatbelt check
│   │   ├── wrong_side_detector.py # Lane-line-based wrong-side analysis
│   │   ├── red_light_detector.py  # Traffic light color detection
│   │   ├── stop_line_detector.py  # Hough line stop-line detection
│   │   ├── parking_detector.py # Heuristic illegal parking detection
│   │   ├── scene_reasoning.py  # Florence-2 scene understanding + template fallback
│   │   ├── image_quality.py    # Quality metrics: brightness, contrast, sharpness, noise
│   │   ├── enhancement_engine.py # Multi-stage image enhancement pipeline
│   │   ├── motion_validator.py # Motion validation for wrong-side detections
│   │   ├── confidence_fusion.py # Multi-detector confidence fusion
│   │   ├── violation_selector.py # Primary violation selection & evidence scoring
│   │   ├── evidence_package.py # PDF evidence report generation
│   │   ├── evidence_generator.py  # Annotated evidence image generation
│   │   ├── risk_scoring.py        # Risk profiling engine
│   │   ├── vehicle_risk.py        # Vehicle-level risk profiles
│   │   ├── repeat_offender.py     # Repeat offender tracking
│   │   ├── hotspot_analytics.py   # Location-based violation clustering
│   │   ├── forecast_engine.py     # Predictive enforcement forecasts
│   │   ├── report_generator.py    # Analytics report generation
│   │   ├── copilot_engine.py      # Natural-language AI copilot
│   │   └── ocr.py                 # License plate OCR with fragment recombination
│   ├── database/               # SQLite database layer
│   ├── utils/                  # Image processing utilities
│   ├── main.py                 # FastAPI application (1200+ lines)
│   ├── config.py               # Configuration & constants
│   ├── download_helmet_model.py # Helmet model auto-downloader
│   └── requirements.txt
├── frontend/                   # Vite + React + TypeScript + Tailwind
│   ├── src/
│   │   └── pages/              # Dashboard, Copilot, Reports, Live, etc.
│   └── ...
├── data/                       # Uploads, evidence images, & PDF reports
├── backend/validation/         # 15-phase validation pipeline (309 images)
├── backend/artifacts/          # Benchmark results & reports
├── generate_ppt.py             # Hackathon PPT generator
└── start.sh                    # One-command launcher (v2)
```

## Violation Detectors

| Violation | Detector | Method | Status |
|---|---|---|---|
| Helmet non-compliance | `helmet_detector.py` | YOLOv8 fine-tuned (v5 crop-based) + HSV emergency fallback | Beta — 77.7% validation pass rate |
| Triple riding | `triple_riding.py` | Rider association scoring (distance/vertical/horizontal/overlap weights) | Active — 54.2% pass rate |
| Motorcycle overloading | `triple_riding.py` | Rider count exceeds occupancy limits (4+ overloading, 5+ extreme) | Active — YOLO detection limit |
| Seatbelt non-compliance | `seatbelt_detector.py` | Hough line transform on car occupant torso | Disabled (hackathon) |
| Wrong-side driving | `wrong_side_detector.py` | Lane line detection + vehicle position analysis | Disabled (hackathon) |
| Red-light violation | `red_light_detector.py` | HSV color analysis on traffic light ROI | Disabled (hackathon) |
| Stop-line violation | `stop_line_detector.py` | Hough line stop-line + vehicle overlap | Disabled (hackathon) |
| Illegal parking | `parking_detector.py` | Spatial & pedestrian context heuristics | Disabled (hackathon) |

## API Endpoints

| Endpoint | Description |
|---|---|
| `POST /api/detect` | Upload image for full violation detection pipeline |
| `GET /api/health` | System health with model status |
| `GET /api/violations` | List violations with filters |
| `GET /api/violations/stats` | Violation statistics |
| `GET /api/violations/analytics` | Analytics by type, day, hour, location |
| `GET /api/intelligence/repeat-offenders` | Top repeat offenders |
| `GET /api/intelligence/vehicle-risk/{plate}` | Vehicle risk profile |
| `GET /api/intelligence/watchlist` | Vehicle watchlist |
| `GET /api/intelligence/hotspots` | Violation hotspot analysis |
| `GET /api/intelligence/forecasts` | Predictive enforcement forecasts |
| `GET /api/evidence/{filename}` | Get annotated evidence image |
| `GET /api/evidence/report/{filename}` | Get PDF evidence report |
| `GET /api/system/performance` | Performance metrics (response times, throughput) |
| `GET /api/system/health` | System health card with model & detector status |
| `GET /api/copilot/query` | Natural-language intelligence query |

Full API docs at `/docs` when running.

## Tech Stack

- **Backend:** Python 3.9+, FastAPI, Uvicorn, SQLite
- **AI:** Ultralytics YOLOv8s, Hugging Face Transformers (Florent-2), EasyOCR, OpenCV, NumPy, SciPy
- **Frontend:** React 19, TypeScript, Vite 6, Tailwind CSS 3
- **Reporting:** fpdf2, Pillow
- **Evaluation:** 309-image benchmark, 15-phase automated validation, Accuracy/Precision/Recall/F1/mAP

## Performance (309-image Benchmark)

| Category | Pass Rate |
|---|---|
| Overall | 77.7% (240/309) |
| HELMET_MISSING | 100% (61/61) |
| TRIPLE_RIDING | 54.2% (13/24) |
| OVERLOADING | 0% (0/15) — YOLO detection limit |
| COMPLIANT | 82.5% (33/40) |
| NON_COMPLIANT | 84.0% (21/25) |
| LOWLIGHT | 82.6% (19/23) |

Pipeline timing: YOLO ~37ms, helmet ~6ms/crop, total ~839ms avg (p95: 1482ms).

## License

MIT
