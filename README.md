# CivicSense v4 — Advanced AR + Smart City Prototype

CivicSense is an educational smart-city prototype for reporting, mapping, managing and tracking civic issues such as potholes, garbage, drainage, street-light faults and water leakage.

## Advanced modules
- Citizen report portal with photo evidence and draggable OpenStreetMap location pin
- AR Civic Scan (`/ar`) with live camera HUD, evidence capture, GPS geotag and device heading
- Duplicate complaint prevention using Haversine distance
- Automatic municipal department routing
- Municipality command center with map, search, filters, priority, staff assignment and status updates
- Citizen tracking with auto-refresh, timeline and map
- Downloadable PDF complaint report and municipality CSV export
- Big Data Lab (`/dataset`) with a bundled 82,000-row synthetic civic dataset (~49 MB raw CSV)
- Dataset generator script in `tools/generate_dataset.py`

## Important dataset note
The bundled dataset is 100% synthetic and is intended only for demonstration, analytics and ML experimentation. It contains no real citizen identity or complaint data. Coordinates are synthetic points around Pune/Pimpri-Chinchwad demo zones.

## Run on Windows / VS Code
Open the folder that directly contains `main.py`, then open VS Code Terminal.

```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Open:
- Citizen portal: http://127.0.0.1:8000
- AR scan: http://127.0.0.1:8000/ar
- Track complaint: http://127.0.0.1:8000/track
- Municipality: http://127.0.0.1:8000/admin
- Data Lab: http://127.0.0.1:8000/dataset
- API docs: http://127.0.0.1:8000/docs

## Presentation flow
1. Open `/ar`, start camera, lock GPS, choose an issue and capture evidence.
2. Submit and note the Complaint ID.
3. Open `/admin`; show the complaint marker and its `AR Camera` capture source.
4. Assign a team, severity and `In Progress` status.
5. Open `/track?id=<ID>` to show live citizen-visible progress.
6. Download the PDF report.
7. Open `/dataset` to demonstrate the 82K-row data layer and download the CSV.

## AR clarification
The included module is a browser-based AR-style field capture prototype: camera feed + HUD + device orientation + GPS/map geotagging. A production version can later be upgraded to full WebXR/ARCore/ARKit spatial anchors and computer-vision object detection.

## Internet requirement
Leaflet loads OpenStreetMap tiles from the internet. The FastAPI backend, SQLite workflow and bundled dataset run locally.
