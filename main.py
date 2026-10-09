from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
from io import BytesIO, StringIO
import csv
import math
import textwrap

import database

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
FRONTEND_DIR = BASE_DIR / "frontend"
MAX_IMAGE_SIZE = 8 * 1024 * 1024

ALLOWED_CATEGORIES = {
    "Pothole",
    "Garbage",
    "Drainage",
    "Street Light",
    "Water Leakage",
    "Illegal Dumping",
    "Damaged Footpath",
    "Other",
}
ALLOWED_STATUSES = ["Reported", "Assigned", "In Progress", "Resolved"]
ALLOWED_SEVERITIES = ["Low", "Medium", "High", "Critical"]

UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="CivicSense - Smart Civic Issue Reporting",
    version="4.0.0",
    description="Map + AR civic reporting, Supabase cloud database support, duplicate prevention, municipal workflow, big-data demo and citizen tracking.",
)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


def department_for(category: str) -> str:
    mapping = {
        "Pothole": "Road Maintenance Department",
        "Garbage": "Solid Waste Department",
        "Drainage": "Drainage & Sewerage Department",
        "Street Light": "Electrical Department",
        "Water Leakage": "Water Supply Department",
        "Illegal Dumping": "Solid Waste Department",
        "Damaged Footpath": "Public Works Department",
        "Other": "General Civic Department",
    }
    return mapping.get(category, "General Civic Department")


def haversine_meters(lat1, lon1, lat2, lon2):
    radius = 6371000
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def validate_coordinates(latitude: float, longitude: float):
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        raise HTTPException(status_code=400, detail="Invalid map coordinates.")


@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/track")
def track_page():
    return FileResponse(FRONTEND_DIR / "track.html")


@app.get("/admin")
def admin_page():
    return FileResponse(FRONTEND_DIR / "admin.html")


@app.get("/ar")
def ar_page():
    return FileResponse(FRONTEND_DIR / "ar.html")


@app.get("/dataset")
def dataset_page():
    return FileResponse(FRONTEND_DIR / "dataset.html")


@app.get("/health")
def health():
    db_info = database.get_db_status()
    return {
        "status": "ok",
        "app": "CivicSense",
        "version": "4.0.0",
        "database": db_info,
        "modules": ["map", "ar-camera", "tracking", "pdf", "csv", "dataset", "supabase-cloud"],
    }


@app.get("/api/db/status")
def db_status_endpoint():
    return database.get_db_status()


@app.post("/api/issues")
async def create_issue(
    reporter_name: str = Form(...),
    reporter_email: str = Form(...),
    reporter_phone: str = Form(""),
    category: str = Form(...),
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    location_label: str = Form(""),
    image: UploadFile = File(...),
    source: str = Form("Citizen Web"),
):
    reporter_name = reporter_name.strip()
    email = reporter_email.strip().lower()
    reporter_phone = reporter_phone.strip()
    category = category.strip()
    description = description.strip()
    location_label = location_label.strip()[:180]
    source = source.strip()[:40] or "Citizen Web"

    if len(reporter_name) < 2:
        raise HTTPException(status_code=400, detail="Please enter your name.")
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail="Please select a valid issue type.")
    if len(description) < 8:
        raise HTTPException(status_code=400, detail="Description should contain at least 8 characters.")

    validate_coordinates(latitude, longitude)

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload a valid image file.")

    contents = await image.read()
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image is too large. Maximum size is 8 MB.")

    # Duplicate check 1: Same citizen + same unresolved category within 60 m
    own_active = database.get_own_active_issues(email, category)
    for issue in own_active:
        if haversine_meters(latitude, longitude, issue["latitude"], issue["longitude"]) <= 60:
            raise HTTPException(
                status_code=409,
                detail=f"Duplicate blocked. You already reported this issue nearby as Complaint #{issue['id']} and it is still {issue['status']}.",
            )

    # Duplicate check 2: Community duplicate within 20 m
    nearby_active = database.get_nearby_active_issues(category, limit=100)
    for issue in nearby_active:
        if haversine_meters(latitude, longitude, issue["latitude"], issue["longitude"]) <= 20:
            raise HTTPException(
                status_code=409,
                detail=f"A similar active complaint already exists here: Complaint #{issue['id']}. Please track that complaint instead.",
            )

    # Upload evidence photo (Supabase Storage bucket or local uploads)
    image_name, image_url = database.upload_evidence(
        file_bytes=contents,
        original_filename=image.filename or "photo.jpg",
        content_type=image.content_type or "image/jpeg",
    )

    now = datetime.now().isoformat(timespec="seconds")
    department = department_for(category)

    issue_payload = {
        "reporter_name": reporter_name,
        "reporter_email": email,
        "reporter_phone": reporter_phone,
        "category": category,
        "description": description,
        "latitude": latitude,
        "longitude": longitude,
        "location_label": location_label,
        "image_name": image_name,
        "image_url": image_url,
        "department": department,
        "severity": "Medium",
        "status": "Reported",
        "assigned_to": "",
        "authority_note": "Complaint received by CivicSense.",
        "source": source,
        "created_at": now,
        "updated_at": now,
    }

    created_issue = database.create_issue(issue_payload)
    return {"message": "Issue reported successfully.", "issue": created_issue}


@app.get("/api/issues")
def get_issues(
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    department: str | None = Query(default=None),
):
    return database.get_issues(status=status, category=category, department=department)


@app.get("/api/issues/export.csv")
def export_issues_csv():
    rows = database.get_issues()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Complaint ID", "Citizen", "Email", "Phone", "Issue", "Description",
        "Location", "Latitude", "Longitude", "Department", "Severity", "Status",
        "Assigned To", "Authority Note", "Source", "Created", "Updated",
    ])
    for row in rows:
        writer.writerow([
            row["id"], row["reporter_name"], row["reporter_email"], row["reporter_phone"],
            row["category"], row["description"], row["location_label"], row["latitude"],
            row["longitude"], row["department"], row["severity"], row["status"],
            row["assigned_to"], row["authority_note"], row["source"], row["created_at"], row["updated_at"],
        ])
    data = output.getvalue().encode("utf-8-sig")
    filename = f"civicsense_reports_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/issues/{issue_id}")
def get_issue(issue_id: int):
    row = database.get_issue(issue_id)
    if not row:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return row


@app.get("/api/issues/{issue_id}/history")
def get_issue_history(issue_id: int):
    row = database.get_issue(issue_id)
    if not row:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return database.get_issue_history(issue_id)


@app.get("/api/issues/{issue_id}/report.pdf")
def download_issue_report(issue_id: int):
    try:
        from reportlab.lib.colors import HexColor
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="PDF support is not installed. Run: pip install reportlab") from exc

    row = database.get_issue(issue_id)
    if not row:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    history = database.get_issue_history(issue_id)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 48

    c.setFillColor(HexColor("#0B1220"))
    c.rect(0, height - 115, width, 115, fill=1, stroke=0)
    c.setFillColor(HexColor("#2DD4BF"))
    c.setFont("Helvetica-Bold", 24)
    c.drawString(margin, height - 62, "CivicSense")
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica", 11)
    c.drawString(margin, height - 84, "Official Civic Complaint Report")
    c.setFont("Helvetica-Bold", 15)
    c.drawRightString(width - margin, height - 66, f"Complaint #{row['id']}")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - margin, height - 86, f"Status: {row['status']}")

    y = height - 150

    def section(title):
        nonlocal y
        if y < 120:
            c.showPage()
            y = height - 55
        c.setFillColor(HexColor("#0F766E"))
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin, y, title.upper())
        y -= 16

    def line(label, value, wrap=78):
        nonlocal y
        value = str(value or "-")
        wrapped = textwrap.wrap(value, wrap) or ["-"]
        if y < 75 + 14 * len(wrapped):
            c.showPage()
            y = height - 55
        c.setFillColor(HexColor("#64748B"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin, y, label)
        c.setFillColor(HexColor("#0F172A"))
        c.setFont("Helvetica", 10)
        first_x = margin + 115
        for index, part in enumerate(wrapped):
            c.drawString(first_x if index == 0 else margin, y, part)
            y -= 14
        y -= 4

    section("Complaint Details")
    line("Issue Type", row["category"])
    line("Description", row["description"], 70)
    line("Severity", row["severity"])
    line("Department", row["department"])
    line("Assigned To", row["assigned_to"] or "Not assigned yet")

    section("Location")
    line("Landmark / Address", row["location_label"] or "Citizen selected map pin")
    line("Coordinates", f"{row['latitude']:.6f}, {row['longitude']:.6f}")
    line("Map", f"https://www.google.com/maps?q={row['latitude']},{row['longitude']}", 66)

    section("Citizen")
    line("Name", row["reporter_name"])
    line("Email", row["reporter_email"])
    line("Phone", row["reporter_phone"] or "Not provided")
    line("Capture Source", row.get("source", "Citizen Web"))

    section("Authority Update")
    line("Latest Note", row["authority_note"] or "No update yet", 70)
    line("Created", row["created_at"])
    line("Last Updated", row["updated_at"])

    section("Activity Timeline")
    for item in history:
        line(item.get("status", ""), f"{item.get('changed_at', '')} - {item.get('note', '')}", 68)

    c.setFillColor(HexColor("#94A3B8"))
    c.setFont("Helvetica", 8)
    c.drawString(margin, 30, "Generated by CivicSense Smart Civic Issue Reporting System")
    c.drawRightString(width - margin, 30, datetime.now().strftime("%d %b %Y, %I:%M %p"))
    c.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="CivicSense_Complaint_{issue_id}.pdf"'},
    )


DATA_DIR = BASE_DIR / "data"
DATASET_PATH = DATA_DIR / "civicsense_large_dataset.csv"
DATASET_SUMMARY_PATH = DATA_DIR / "dataset_summary.json"


@app.get("/api/dataset/stats")
def dataset_stats():
    import json
    if not DATASET_SUMMARY_PATH.exists():
        raise HTTPException(status_code=404, detail="Dataset summary not found.")
    return json.loads(DATASET_SUMMARY_PATH.read_text(encoding="utf-8"))


@app.get("/api/dataset/sample")
def dataset_sample(limit: int = Query(default=12, ge=1, le=50)):
    if not DATASET_PATH.exists():
        raise HTTPException(status_code=404, detail="Dataset not found.")
    rows = []
    with DATASET_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            rows.append(row)
            if index + 1 >= limit:
                break
    return rows


@app.get("/api/dataset/download")
def dataset_download():
    if not DATASET_PATH.exists():
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return FileResponse(
        DATASET_PATH,
        media_type="text/csv",
        filename="CivicSense_Large_Synthetic_Dataset.csv",
    )


class StatusUpdate(BaseModel):
    status: str
    severity: str = "Medium"
    assigned_to: str = ""
    note: str = ""


@app.patch("/api/issues/{issue_id}/status")
def update_status(issue_id: int, data: StatusUpdate):
    if data.status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status.")
    if data.severity not in ALLOWED_SEVERITIES:
        raise HTTPException(status_code=400, detail="Invalid severity.")

    existing = database.get_issue(issue_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    now = datetime.now().isoformat(timespec="seconds")
    note = data.note.strip() or f"Status changed to {data.status}."
    assigned_to = data.assigned_to.strip()

    updated = database.update_issue_status(
        issue_id=issue_id,
        status=data.status,
        severity=data.severity,
        assigned_to=assigned_to,
        note=note,
        updated_at=now,
    )
    return {"message": "Complaint updated.", "issue": updated}


@app.get("/api/dashboard/stats")
def dashboard_stats():
    return database.get_dashboard_stats(ALLOWED_STATUSES)
