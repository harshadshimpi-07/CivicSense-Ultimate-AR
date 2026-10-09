import os
import uuid
import math
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger("civicsense.db")

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

DB_PATH = BASE_DIR / "civic.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "civicsense-uploads").strip()
DB_MODE = os.getenv("DB_MODE", "auto").strip().lower()

_supabase_client = None
_is_supabase_connected = False


def init_supabase():
    global _supabase_client, _is_supabase_connected
    if DB_MODE == "sqlite":
        logger.info("DB_MODE is set to 'sqlite'. Using local SQLite database.")
        _supabase_client = None
        _is_supabase_connected = False
        return

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.info("Supabase credentials not configured in .env. Running on local SQLite database.")
        _supabase_client = None
        _is_supabase_connected = False
        return

    try:
        from supabase import create_client, Client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Test connection with a lightweight probe
        _supabase_client.table("issues").select("id").limit(1).execute()
        _is_supabase_connected = True
        logger.info(f"Connected to Supabase cloud database at {SUPABASE_URL}")
    except Exception as exc:
        logger.warning(f"Failed to connect to Supabase: {exc}. Falling back to local SQLite.")
        _supabase_client = None
        _is_supabase_connected = False


def is_supabase_active() -> bool:
    global _supabase_client, _is_supabase_connected
    if _supabase_client is None and SUPABASE_URL and SUPABASE_KEY and DB_MODE != "sqlite":
        init_supabase()
    return bool(_supabase_client and _is_supabase_connected)


def get_db_status() -> dict:
    active_supabase = is_supabase_active()
    return {
        "mode": "supabase" if active_supabase else "sqlite",
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_KEY),
        "supabase_connected": active_supabase,
        "supabase_url": SUPABASE_URL if active_supabase else "",
        "storage_bucket": SUPABASE_BUCKET,
        "fallback_sqlite": not active_supabase,
        "sqlite_path": str(DB_PATH),
    }


# ==============================================================================
# SQLite Helpers
# ==============================================================================
def get_sqlite_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_column(conn, table: str, column: str, definition: str):
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    if is_supabase_active():
        logger.info("Supabase active. Skipping local SQLite schema creation.")
        return

    conn = get_sqlite_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_name TEXT NOT NULL,
            reporter_email TEXT NOT NULL,
            reporter_phone TEXT DEFAULT '',
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            location_label TEXT DEFAULT '',
            image_name TEXT NOT NULL,
            image_url TEXT DEFAULT '',
            department TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'Medium',
            status TEXT NOT NULL DEFAULT 'Reported',
            assigned_to TEXT DEFAULT '',
            authority_note TEXT DEFAULT '',
            source TEXT NOT NULL DEFAULT 'Citizen Web',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    ensure_column(conn, "issues", "location_label", "TEXT DEFAULT ''")
    ensure_column(conn, "issues", "image_url", "TEXT DEFAULT ''")
    ensure_column(conn, "issues", "source", "TEXT NOT NULL DEFAULT 'Citizen Web'")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            note TEXT DEFAULT '',
            changed_at TEXT NOT NULL,
            FOREIGN KEY(issue_id) REFERENCES issues(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()
    conn.close()


# ==============================================================================
# Image Upload / Storage
# ==============================================================================
def upload_evidence(file_bytes: bytes, original_filename: str, content_type: str = "image/jpeg") -> tuple[str, str]:
    """
    Saves image to Supabase Storage if configured and available,
    otherwise saves to local uploads/ directory.
    Returns: (image_name, image_url)
    """
    suffix = Path(original_filename or "photo.jpg").suffix.lower()
    if suffix not in [".jpg", ".jpeg", ".png", ".webp"]:
        suffix = ".jpg"
    image_name = f"{uuid.uuid4().hex}{suffix}"

    # Always keep a local copy for fallback / offline viewing
    local_path = UPLOAD_DIR / image_name
    local_path.write_bytes(file_bytes)
    local_url = f"/uploads/{image_name}"

    if is_supabase_active():
        try:
            # Upload to Supabase Storage bucket
            _supabase_client.storage.from_(SUPABASE_BUCKET).upload(
                path=image_name,
                file=file_bytes,
                file_options={"content-type": content_type or "image/jpeg", "upsert": "true"},
            )
            # Retrieve public URL
            public_url = _supabase_client.storage.from_(SUPABASE_BUCKET).get_public_url(image_name)
            return image_name, public_url
        except Exception as err:
            logger.warning(f"Could not upload image to Supabase Storage: {err}. Using local path.")
            return image_name, local_url

    return image_name, local_url


# ==============================================================================
# Model Normalizer
# ==============================================================================
def normalize_issue_dict(row: dict | sqlite3.Row) -> dict:
    if isinstance(row, sqlite3.Row):
        d = dict(row)
    else:
        d = dict(row)

    image_name = d.get("image_name") or ""
    image_url = d.get("image_url") or ""
    if not image_url and image_name:
        image_url = f"/uploads/{image_name}"

    return {
        "id": int(d["id"]),
        "reporter_name": d.get("reporter_name", ""),
        "reporter_email": d.get("reporter_email", ""),
        "reporter_phone": d.get("reporter_phone", "") or "",
        "category": d.get("category", ""),
        "description": d.get("description", ""),
        "latitude": float(d.get("latitude", 0.0)),
        "longitude": float(d.get("longitude", 0.0)),
        "location_label": d.get("location_label", "") or "",
        "image_name": image_name,
        "image_url": image_url,
        "department": d.get("department", ""),
        "severity": d.get("severity", "Medium"),
        "status": d.get("status", "Reported"),
        "assigned_to": d.get("assigned_to", "") or "",
        "authority_note": d.get("authority_note", "") or "",
        "source": d.get("source", "Citizen Web"),
        "created_at": str(d.get("created_at", "")),
        "updated_at": str(d.get("updated_at", "")),
    }


# ==============================================================================
# Query Methods
# ==============================================================================
def get_own_active_issues(email: str, category: str) -> list[dict]:
    if is_supabase_active():
        try:
            res = (
                _supabase_client.table("issues")
                .select("*")
                .eq("reporter_email", email)
                .eq("category", category)
                .neq("status", "Resolved")
                .execute()
            )
            return [normalize_issue_dict(r) for r in res.data]
        except Exception as exc:
            logger.error(f"Supabase query error: {exc}")

    conn = get_sqlite_conn()
    rows = conn.execute(
        "SELECT * FROM issues WHERE reporter_email = ? AND category = ? AND status != 'Resolved'",
        (email, category),
    ).fetchall()
    conn.close()
    return [normalize_issue_dict(r) for r in rows]


def get_nearby_active_issues(category: str, limit: int = 100) -> list[dict]:
    if is_supabase_active():
        try:
            res = (
                _supabase_client.table("issues")
                .select("*")
                .eq("category", category)
                .neq("status", "Resolved")
                .order("id", desc=True)
                .limit(limit)
                .execute()
            )
            return [normalize_issue_dict(r) for r in res.data]
        except Exception as exc:
            logger.error(f"Supabase query error: {exc}")

    conn = get_sqlite_conn()
    rows = conn.execute(
        "SELECT * FROM issues WHERE category = ? AND status != 'Resolved' ORDER BY id DESC LIMIT ?",
        (category, limit),
    ).fetchall()
    conn.close()
    return [normalize_issue_dict(r) for r in rows]


def create_issue(issue_data: dict) -> dict:
    if is_supabase_active():
        try:
            res = _supabase_client.table("issues").insert(issue_data).execute()
            if res.data:
                created = res.data[0]
                # Log initial status history
                _supabase_client.table("status_history").insert({
                    "issue_id": created["id"],
                    "status": "Reported",
                    "note": "Complaint submitted by citizen with map location and photo evidence.",
                    "changed_at": issue_data["created_at"]
                }).execute()
                return normalize_issue_dict(created)
        except Exception as exc:
            logger.error(f"Supabase insert error: {exc}. Trying SQLite fallback.")

    conn = get_sqlite_conn()
    cursor = conn.execute(
        """
        INSERT INTO issues (
            reporter_name, reporter_email, reporter_phone, category, description,
            latitude, longitude, location_label, image_name, image_url, department, severity,
            status, assigned_to, authority_note, source, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            issue_data["reporter_name"],
            issue_data["reporter_email"],
            issue_data.get("reporter_phone", ""),
            issue_data["category"],
            issue_data["description"],
            issue_data["latitude"],
            issue_data["longitude"],
            issue_data.get("location_label", ""),
            issue_data["image_name"],
            issue_data.get("image_url", ""),
            issue_data["department"],
            issue_data.get("severity", "Medium"),
            issue_data.get("status", "Reported"),
            issue_data.get("assigned_to", ""),
            issue_data.get("authority_note", "Complaint received by CivicSense."),
            issue_data.get("source", "Citizen Web"),
            issue_data["created_at"],
            issue_data["updated_at"],
        ),
    )
    issue_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO status_history (issue_id, status, note, changed_at) VALUES (?, ?, ?, ?)",
        (issue_id, "Reported", "Complaint submitted by citizen with map location and photo evidence.", issue_data["created_at"]),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
    conn.close()
    return normalize_issue_dict(row)


def get_issues(status: str | None = None, category: str | None = None, department: str | None = None) -> list[dict]:
    if is_supabase_active():
        try:
            query = _supabase_client.table("issues").select("*")
            if status:
                query = query.eq("status", status)
            if category:
                query = query.eq("category", category)
            if department:
                query = query.eq("department", department)
            res = query.order("id", desc=True).execute()
            return [normalize_issue_dict(r) for r in res.data]
        except Exception as exc:
            logger.error(f"Supabase get_issues error: {exc}")

    conn = get_sqlite_conn()
    query = "SELECT * FROM issues WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if category:
        query += " AND category = ?"
        params.append(category)
    if department:
        query += " AND department = ?"
        params.append(department)
    query += " ORDER BY id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [normalize_issue_dict(r) for r in rows]


def get_issue(issue_id: int) -> dict | None:
    if is_supabase_active():
        try:
            res = _supabase_client.table("issues").select("*").eq("id", issue_id).execute()
            if res.data:
                return normalize_issue_dict(res.data[0])
            return None
        except Exception as exc:
            logger.error(f"Supabase get_issue error: {exc}")

    conn = get_sqlite_conn()
    row = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
    conn.close()
    return normalize_issue_dict(row) if row else None


def get_issue_history(issue_id: int) -> list[dict]:
    if is_supabase_active():
        try:
            res = (
                _supabase_client.table("status_history")
                .select("status, note, changed_at")
                .eq("issue_id", issue_id)
                .order("id", desc=False)
                .execute()
            )
            return res.data
        except Exception as exc:
            logger.error(f"Supabase get_issue_history error: {exc}")

    conn = get_sqlite_conn()
    rows = conn.execute(
        "SELECT status, note, changed_at FROM status_history WHERE issue_id = ? ORDER BY id ASC",
        (issue_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_issue_status(issue_id: int, status: str, severity: str, assigned_to: str, note: str, updated_at: str) -> dict | None:
    if is_supabase_active():
        try:
            update_payload = {
                "status": status,
                "severity": severity,
                "assigned_to": assigned_to,
                "authority_note": note,
                "updated_at": updated_at,
            }
            res = _supabase_client.table("issues").update(update_payload).eq("id", issue_id).execute()
            if res.data:
                _supabase_client.table("status_history").insert({
                    "issue_id": issue_id,
                    "status": status,
                    "note": note,
                    "changed_at": updated_at,
                }).execute()
                return normalize_issue_dict(res.data[0])
        except Exception as exc:
            logger.error(f"Supabase update error: {exc}")

    conn = get_sqlite_conn()
    conn.execute(
        """
        UPDATE issues
        SET status = ?, severity = ?, assigned_to = ?, authority_note = ?, updated_at = ?
        WHERE id = ?
        """,
        (status, severity, assigned_to, note, updated_at, issue_id),
    )
    conn.execute(
        "INSERT INTO status_history (issue_id, status, note, changed_at) VALUES (?, ?, ?, ?)",
        (issue_id, status, note, updated_at),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
    conn.close()
    return normalize_issue_dict(updated) if updated else None


def get_dashboard_stats(allowed_statuses: list[str]) -> dict:
    if is_supabase_active():
        try:
            all_issues = _supabase_client.table("issues").select("status, severity").execute().data
            total = len(all_issues)
            by_status = {status: 0 for status in allowed_statuses}
            priority = 0
            for item in all_issues:
                st = item.get("status", "Reported")
                sev = item.get("severity", "Medium")
                if st in by_status:
                    by_status[st] += 1
                if sev in ["High", "Critical"] and st != "Resolved":
                    priority += 1
            resolved = by_status.get("Resolved", 0)
            resolution_rate = round((resolved / total) * 100) if total else 0
            return {
                "total": total,
                "by_status": by_status,
                "priority_open": priority,
                "resolution_rate": resolution_rate,
                "storage_mode": "supabase",
            }
        except Exception as exc:
            logger.error(f"Supabase stats error: {exc}")

    conn = get_sqlite_conn()
    total = conn.execute("SELECT COUNT(*) AS c FROM issues").fetchone()["c"]
    rows = conn.execute("SELECT status, COUNT(*) AS c FROM issues GROUP BY status").fetchall()
    priority = conn.execute("SELECT COUNT(*) AS c FROM issues WHERE severity IN ('High','Critical') AND status != 'Resolved'").fetchone()["c"]
    by_status = {status: 0 for status in allowed_statuses}
    for row in rows:
        if row["status"] in by_status:
            by_status[row["status"]] = row["c"]
    conn.close()
    resolved = by_status["Resolved"]
    resolution_rate = round((resolved / total) * 100) if total else 0
    return {
        "total": total,
        "by_status": by_status,
        "priority_open": priority,
        "resolution_rate": resolution_rate,
        "storage_mode": "sqlite",
    }


# Initialize on import
init_supabase()
init_db()
