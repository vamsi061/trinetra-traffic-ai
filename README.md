# TRINETRA AI

**AI-Powered Traffic Violation Detection and Enforcement Intelligence Platform**

TRINETRA AI is a comprehensive traffic violation detection system built for the Flipkart Gridlock Hackathon. It uses computer vision (YOLOv8, EasyOCR) to automatically detect traffic violations from uploaded images, extract license plate numbers, generate evidence, and provide analytics.

## Features

### Violation Detection
- **No Helmet Detection** - Identifies motorcycle riders without helmets
- **Triple Riding Detection** - Detects motorcycles carrying more than 2 persons
- **License Plate Recognition** - OCR-based vehicle number extraction

### System Capabilities
- Image preprocessing (brightness, contrast, noise reduction, shadow handling, low-light enhancement)
- YOLOv8-based object detection (motorcycles, cars, buses, trucks, persons)
- Evidence generation with annotated bounding boxes and violation markers
- SQLite database for violation records
- Interactive Streamlit dashboard with analytics
- AI Copilot with natural language query interface

## Project Structure

```
trinetra-ai/
├── app.py                    # Main Streamlit application
├── config.py                 # Configuration and constants
├── requirements.txt          # Python dependencies
├── README.md                 # Documentation
├── pages/
│   ├── upload.py             # Image upload and analysis page
│   ├── records.py            # Violation records page
│   ├── analytics.py          # Analytics dashboard
│   └── copilot.py            # AI copilot chat interface
├── ai/
│   ├── detector.py           # YOLOv8 object detection engine
│   ├── helmet_detector.py    # Helmet violation detection
│   ├── triple_riding.py      # Triple riding detection
│   ├── ocr.py                # License plate OCR
│   └── evidence_generator.py # Evidence image generation
├── database/
│   ├── db.py                 # SQLite database operations
│   └── models.py             # Data models
├── utils/
│   └── image_processing.py   # Image preprocessing functions
└── data/
    ├── uploads/              # Uploaded images
    └── evidence/             # Generated evidence images
```

## Installation

### Prerequisites
- Python 3.11+
- pip

### Setup

1. **Clone or extract the project**
   ```bash
   cd trinetra-ai
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   > **Note:** First run will download YOLOv8 model (~6MB) and EasyOCR models (~100MB).

## Running the Application

### Streamlit Dashboard
```bash
streamlit run app.py
```
Launch: **http://localhost:8501**

### FastAPI Backend (Optional)
```bash
uvicorn main:app --reload --port 8000
```
API: **http://localhost:8000**

## Usage Guide

### 1. Upload & Analyze
1. Navigate to **Upload Image** page
2. Upload a traffic image (JPG, PNG, BMP)
3. System runs full analysis pipeline
4. View detections, violations, and evidence

### 2. View Records
- Browse all violation records
- Filter by vehicle number, violation type, date
- Download records as CSV

### 3. Analytics Dashboard
- Violations by type (pie chart, bar chart)
- Daily violation trends (line chart, area chart)
- Top repeat offenders
- Monthly trend analysis

### 4. AI Copilot
Ask questions in natural language:
- "Show helmet violations"
- "Show violation statistics"
- "Show repeat offenders"
- "Show records for vehicle KA-01-AB-1234"
- "Show monthly trend"

## Technology Stack

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit |
| Backend | FastAPI |
| Computer Vision | Ultralytics YOLOv8 |
| OCR | EasyOCR |
| Image Processing | OpenCV |
| Database | SQLite |
| Visualization | Plotly |
| Data Handling | Pandas |

## System Architecture

```
Upload Image → Image Enhancement → YOLO Detection → Violation Detection
                                                       ↓
License Plate OCR ← Vehicle Detection ← Triple Riding ← Helmet Check
       ↓
Evidence Generation → Database Storage → Analytics Dashboard
```

## Database Schema

```sql
CREATE TABLE violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_number TEXT DEFAULT '',
    vehicle_type TEXT DEFAULT '',
    violation_type TEXT NOT NULL,
    confidence REAL DEFAULT 0.0,
    image_path TEXT DEFAULT '',
    evidence_path TEXT DEFAULT '',
    timestamp TEXT NOT NULL
);
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/detect` | Analyze uploaded image |
| GET | `/api/violations` | Get all violations |
| GET | `/api/violations/stats` | Get violation statistics |
| GET | `/api/violations/analytics` | Get analytics data |

## License

This project is created for the Flipkart Gridlock Hackathon.
