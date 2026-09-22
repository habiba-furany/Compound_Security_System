# Compound Security System

A computer vision system for compound security. It handles vehicle entry/exit at the main gate, monitors fire/smoke in different areas, and tracks parking.

## What it does

**Gate control**
- Detects the vehicle type at the gate (car / tuk-tuk / tricycle)
- Denies entry automatically for restricted vehicle types
- Reads the license plate 
- Detects vehicle color
- Logs entry time, and later matches the plate on exit to log the exit time
- Checks plates against a blacklist

**Fire & smoke monitoring**
- Two camera feeds (Area 1, Area 2), supports both images and video
- Draws bounding boxes on detected fire/smoke
- Shows live alert counts and threat level (LOW / MEDIUM / HIGH) per area

**Parking**
- Tracks free/occupied spots

## Project structure

```
project/
├── backend/        # FastAPI app, exposes the endpoints
├── frontend/        # Streamlit Interface
├── core/             # detection/classification logic per model (plate, vehicle, color, fire, parking)
├── database/        # SQLite setup and queries
├── models/           # trained model weights (.pt / .keras)
├── requirements.txt
└── Dockerfile
```

## How it's built

Each model lives in its own function in `core/`. The `gate_logic.py` file wires them together in order: check vehicle type first (fastest way to reject a banned type before doing any extra work), then plate, then blacklist, then color/brand, then log to the database.

FastAPI just exposes this as a few endpoints grouped by what they do (`/gate/entry`, `/gate/exit`, `/safety/fire-smoke`, `/parking/status`), not one endpoint per model. Streamlit calls these endpoints and displays the results.

## Tech used

- YOLO (Ultralytics) — vehicle detection, fire/smoke detection , license plate detection
- OCR — license plate reading
- TensorFlow/Keras — vehicle type classification
- OpenCV — color detection (HSV), image processing
- FastAPI — backend
- Streamlit — interface
- SQLite — storage

## Running it locally

```bash
# backend
uvicorn backend.main:app --reload

# frontend (separate terminal)
streamlit run frontend/app.py
```

