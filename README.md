# Smart Security System

A runnable campus smart-security demo system built on Flask, OpenCV, YOLOv8, DeepSORT, and SQLite.

## Features
- Single-camera real-time monitoring page
- YOLOv8 pedestrian detection with background-subtraction fallback
- DeepSORT multi-object tracking with IoU fallback
- Electronic-fence intrusion detection
- Running and gathering alert rules
- Alert center with filterable event records
- Dashboard page with runtime metrics and alert statistics
- SQLite persistence for alert history

## Project Structure
```text
smart_security_system/
├── app.py                     # Flask entry
├── config.py                  # App config
├── core/
│   ├── detector.py            # Detection backend
│   ├── tracker.py             # Tracking backend
│   ├── rules.py               # Intrusion/running/gathering rules
│   ├── pipeline.py            # Main video pipeline
│   ├── storage.py             # SQLite alert store
│   └── models.py              # Data models
├── web/
│   ├── static/
│   │   ├── app.css            # Shared UI style
│   │   └── app.js             # Shared browser helpers
│   └── templates/
│       ├── base.html          # Shared layout
│       ├── index.html         # Monitoring page
│       ├── alerts.html        # Alert center
│       └── dashboard.html     # Statistics dashboard
└── data/
    └── alerts.db              # SQLite database
```

## Quick Start

Environment requirements:
- Python 3.10 or newer
- `pip`
- Camera access if running live input
- Recommended OS: macOS / Linux / Windows with OpenCV support

1. Create a virtual environment and install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run with camera or local video:
```bash
python app.py --source 0
# or
python app.py --source data/demo.mp4
```

3. Open pages in the browser:
- Monitoring page: `http://127.0.0.1:5000/`
- Alert center: `http://127.0.0.1:5000/alerts`
- Dashboard page: `http://127.0.0.1:5000/dashboard`

## Main APIs
- `GET /api/alerts?limit=100&type=intrusion`
- `GET /api/alerts/summary`
- `GET /api/stats`
- `GET /api/dashboard`
- `POST /api/fence`
- `POST /api/rules`

## Demo Notes
- If `ultralytics` cannot load successfully, the detector falls back to background subtraction.
- If `deep-sort-realtime` is unavailable, the tracker falls back to a simple IoU tracker.
- Default class filter is `person`.
- Default database path is `data/alerts.db`.

## Suggested GitHub Upload Workflow

Recommended repository name:
- `smart-security-system-demo`
- `campus-smart-security-demo`

Recommended upload scope:
- `app.py`
- `config.py`
- `requirements.txt`
- `README.md`
- `core/`
- `web/`

Do not upload:
- local database
- snapshots
- demo videos
- thesis scripts
- traces
- virtual environment files
