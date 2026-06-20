# TRINETRA AI — Traffic Violation Detection Platform

AI-powered traffic enforcement intelligence platform for smart cities. Detects violations from uploaded images, generates evidence reports, and provides predictive enforcement analytics.

## Features

- **AI Detection** — Motorcycles, cars, persons, buses, trucks via YOLOv8 (Ultralytics)
- **License Plate OCR** — Reads vehicle numbers using EasyOCR
- **Violation Detection** — Helmet, triple riding, seatbelt, wrong-side, illegal parking
- **Risk Scoring** — Enhanced risk profiling with repeat-offender multipliers
- **Evidence Reports** — Auto-generated PDF reports via fpdf2
- **Repeat Offender Tracking** — Vehicle-level violation history and risk scoring
- **Hotspot Analytics** — Location-based violation clustering
- **Forecast Engine** — Predictive enforcement recommendations
- **AI Copilot** — Natural-language query engine for intelligence data
- **Enforcement Dashboard** — Smart city decision support with charts & recommendations

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

## Project Structure

```
├── backend/
│   ├── ai/                  # AI models & detection modules
│   │   ├── detector.py      # YOLOv8 object detection
│   │   ├── ocr.py           # License plate OCR
│   │   ├── helmet_detector.py
│   │   ├── triple_riding.py
│   │   ├── seatbelt_detector.py
│   │   ├── wrong_side_detector.py
│   │   ├── parking_detector.py
│   │   ├── evidence_package.py
│   │   ├── evidence_generator.py
│   │   ├── risk_scoring.py
│   │   ├── vehicle_risk.py
│   │   ├── repeat_offender.py
│   │   ├── hotspot_analytics.py
│   │   ├── forecast_engine.py
│   │   ├── report_generator.py
│   │   ├── copilot_engine.py
│   │   └── quality_assessment.py
│   ├── database/            # SQLite database layer
│   ├── utils/               # Image processing utilities
│   ├── main.py              # FastAPI application
│   ├── config.py
│   └── requirements.txt
├── frontend/                # Vite + React + TypeScript + Tailwind
│   ├── src/
│   │   └── pages/           # Dashboard, Copilot, Reports, etc.
│   └── ...
├── data/                    # Uploads & generated reports
└── start.sh                 # One-command launcher
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `POST /api/detect` | Upload image for violation detection |
| `GET /api/intelligence/repeat-offenders` | Top repeat offenders |
| `GET /api/intelligence/hotspots` | Violation hotspot analysis |
| `GET /api/intelligence/forecasts` | Predictive enforcement forecasts |
| `POST /api/intelligence/reports/generate` | Generate PDF report |
| `POST /api/intelligence/copilot/query` | AI Copilot natural-language query |

Full API docs at `/docs` when running.

## Tech Stack

- **Backend:** Python, FastAPI, Uvicorn, SQLite
- **AI:** Ultralytics YOLOv8, EasyOCR, OpenCV
- **Frontend:** React, TypeScript, Vite, Tailwind CSS
- **Reporting:** fpdf2

## License

MIT
