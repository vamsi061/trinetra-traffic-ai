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

**Hackathon Alignment**: Developed for the *Automated Photo Identification and Classification for Traffic Violations Using Computer Vision* challenge — covering image preprocessing, vehicle/pedestrian detection, violation detection (helmet, seatbelt, triple riding, wrong-side, red-light, stop-line, illegal parking), license plate OCR, evidence generation, and performance evaluation (Accuracy, Precision, Recall, F1, mAP).

## Features

- **8 Violation Detectors** — Helmet non-compliance, seatbelt non-compliance, triple riding, wrong-side driving, red-light violation, stop-line violation, illegal parking, motorcycle overloading
- **License Plate OCR** — Full plate text extraction via EasyOCR with fragment recombination ("KA01" + "AB" + "1234" → "KA01AB1234")
- **Vehicle & Road User Detection** — YOLOv8 detects cars, motorcycles, buses, trucks, persons, traffic lights, stop signs
- **Explainable AI** — Per-violation confidence, reliability badge, human review status, and enforcement recommendation
- **Risk Scoring** — Enhanced profiling with repeat-offender multipliers, location risk, time-of-day risk
- **Evidence Reports** — Professional PDF reports (fpdf2) with case info, quality assessment, violation table, officer notes
- **Repeat Offender Tracking** — Vehicle-level violation history and risk scoring
- **Hotspot Analytics** — Location-based violation clustering
- **Forecast Engine** — Predictive enforcement recommendations
- **AI Copilot** — Natural-language query engine for intelligence data
- **Enforcement Dashboard** — Smart city decision support with charts & recommendations
- **Robust Preprocessing** — Handles low light, rain, shadows, motion blur via `enhance_image()`
- **Performance Evaluation** — `evaluate.py` computes Accuracy, Precision, Recall, F1-score, mAP with 11-point interpolation

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+
- npm

### Run

```bash
bash start.sh
```

Opens at **http://localhost:8000**.

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
│   │   ├── locate_anything.py   # YOLOv8 object detection (fallback chain)
│   │   ├── ocr.py               # License plate OCR with fragment recombination
│   │   ├── helmet_detector.py   # YOLO helmet model + HSV fallback
│   │   ├── triple_riding.py     # Rider association & occupancy analysis
│   │   ├── seatbelt_detector.py # Car occupant seatbelt check (strict containment)
│   │   ├── wrong_side_detector.py # Lane-line-based wrong-side analysis
│   │   ├── red_light_detector.py  # Traffic light color + stop line crossing
│   │   ├── stop_line_detector.py  # Hough line stop-line detection
│   │   ├── parking_detector.py # Heuristic illegal parking detection
│   │   ├── rider_association.py   # Person-motorcycle association scoring
│   │   ├── evidence_package.py # PDF evidence report generation
│   │   ├── evidence_generator.py  # Annotated evidence image generation
│   │   ├── risk_scoring.py        # Risk profiling engine
│   │   ├── vehicle_risk.py        # Vehicle-level risk profiles
│   │   ├── repeat_offender.py     # Repeat offender tracking
│   │   ├── hotspot_analytics.py   # Location-based violation clustering
│   │   ├── forecast_engine.py     # Predictive enforcement forecasts
│   │   ├── report_generator.py    # Analytics report generation
│   │   ├── copilot_engine.py      # Natural-language AI copilot
│   │   └── quality_assessment.py  # Image quality assessment
│   ├── database/               # SQLite database layer
│   ├── utils/                  # Image processing utilities
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration & constants
│   ├── evaluate.py             # Performance evaluation (Accuracy, Precision, Recall, F1, mAP)
│   └── requirements.txt
├── frontend/                   # Vite + React + TypeScript + Tailwind
│   ├── src/
│   │   └── pages/              # Dashboard, Copilot, Reports, etc.
│   └── ...
├── data/                       # Uploads & generated reports
├── tests/                      # Test scripts & sample images
│   ├── samples/                # 20 test images (helmet, OCR, parking, etc.)
│   └── test_samples.py         # Automated test suite (20 cases)
└── start.sh                    # One-command launcher
```

## Violation Detectors

| Violation | Detector | Method |
|---|---|---|
| Helmet non-compliance | `helmet_detector.py` | YOLOv8 fine-tuned helmet model + HSV fallback |
| Seatbelt non-compliance | `seatbelt_detector.py` | Hough line transform on car occupant torso |
| Triple riding | `triple_riding.py` | Rider association scoring (distance, vertical, horizontal, overlap) |
| Wrong-side driving | `wrong_side_detector.py` | Lane line detection + vehicle position analysis |
| Red-light violation | `red_light_detector.py` | YOLO traffic light class (9) + HSV color analysis |
| Stop-line violation | `stop_line_detector.py` | Hough line stop-line detection + vehicle position |
| Illegal parking | `parking_detector.py` | Spatial & pedestrian context heuristics |
| Motorcycle overloading | `triple_riding.py` | Rider count exceeds occupancy limits |

## API Endpoints

| Endpoint | Description |
|---|---|
| `POST /api/detect` | Upload image for violation detection |
| `GET /api/violations` | List violations with filters |
| `GET /api/violations/stats` | Violation statistics |
| `GET /api/violations/analytics` | Analytics by type, day, hour, location |
| `GET /api/intelligence/repeat-offenders` | Top repeat offenders |
| `GET /api/intelligence/vehicle-risk/{plate}` | Vehicle risk profile |
| `GET /api/intelligence/watchlist` | Vehicle watchlist |
| `GET /api/intelligence/hotspots` | Violation hotspot analysis |
| `GET /api/intelligence/forecasts` | Predictive enforcement forecasts |
| `GET /api/evidence/{filename}` | Get evidence image |
| `GET /api/evidence/report/{filename}` | Get PDF evidence report |

Full API docs at `/docs` when running.

## Tech Stack

- **Backend:** Python, FastAPI, Uvicorn, SQLite
- **AI:** Ultralytics YOLOv8, EasyOCR, OpenCV, NumPy
- **Frontend:** React, TypeScript, Vite, Tailwind CSS
- **Reporting:** fpdf2
- **Evaluation:** Accuracy, Precision, Recall, F1-score, mAP (11-point interpolation)

## License

MIT
