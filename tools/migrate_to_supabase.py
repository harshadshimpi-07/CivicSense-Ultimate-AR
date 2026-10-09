"""
CivicSense - SQLite to Supabase Migration Utility
Transfers all local SQLite complaints & status history into Supabase Cloud Database.
"""

import sys
import sqlite3
from pathlib import Path

# Add parent directory to path so we can import database module
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import database

def migrate():
    print("=" * 60)
    print(" CivicSense — SQLite to Supabase Cloud Migration Tool")
    print("=" * 60)

    if not database.SUPABASE_URL or not database.SUPABASE_KEY:
        print("\n[!] ERROR: Supabase credentials not found in .env file.")
        print("Please configure SUPABASE_URL and SUPABASE_KEY in CivicSense_Ultimate_AR/.env first.\n")
        return

    if not database.is_supabase_active():
        print("\n[!] ERROR: Unable to connect to Supabase.")
        print("Check your SUPABASE_URL, SUPABASE_KEY, and ensure you ran 'supabase_schema.sql' in the Supabase SQL Editor.\n")
        return

    if not database.DB_PATH.exists():
        print(f"\n[!] SQLite database not found at {database.DB_PATH}. Nothing to migrate.\n")
        return

    conn = sqlite3.connect(database.DB_PATH)
    conn.row_factory = sqlite3.Row

    # 1. Migrate issues
    issues = conn.execute("SELECT * FROM issues ORDER BY id ASC").fetchall()
    print(f"\nFound {len(issues)} complaint(s) in local SQLite database.")

    client = database._supabase_client
    migrated_count = 0
    for issue in issues:
        d = dict(issue)
        issue_id = d["id"]
        print(f"Migrating Complaint #{issue_id} ({d['category']})...", end=" ")
        
        # Prepare record
        payload = {
            "id": issue_id,
            "reporter_name": d["reporter_name"],
            "reporter_email": d["reporter_email"],
            "reporter_phone": d.get("reporter_phone", ""),
            "category": d["category"],
            "description": d["description"],
            "latitude": float(d["latitude"]),
            "longitude": float(d["longitude"]),
            "location_label": d.get("location_label", ""),
            "image_name": d["image_name"],
            "image_url": d.get("image_url", f"/uploads/{d['image_name']}"),
            "department": d["department"],
            "severity": d.get("severity", "Medium"),
            "status": d.get("status", "Reported"),
            "assigned_to": d.get("assigned_to", ""),
            "authority_note": d.get("authority_note", ""),
            "source": d.get("source", "Citizen Web"),
            "created_at": d["created_at"],
            "updated_at": d["updated_at"]
        }

        try:
            client.table("issues").upsert(payload).execute()
            print("OK")
            migrated_count += 1
        except Exception as err:
            print(f"FAILED: {err}")

    # 2. Migrate status history
    history = conn.execute("SELECT * FROM status_history ORDER BY id ASC").fetchall()
    print(f"\nFound {len(history)} status history record(s).")
    hist_count = 0
    for h in history:
        hd = dict(h)
        try:
            client.table("status_history").upsert({
                "id": hd["id"],
                "issue_id": hd["issue_id"],
                "status": hd["status"],
                "note": hd.get("note", ""),
                "changed_at": hd["changed_at"]
            }).execute()
            hist_count += 1
        except Exception as err:
            print(f"History #{hd['id']} failed: {err}")

    conn.close()
    print(f"\n[✓] Migration Complete! Successfully migrated {migrated_count} complaints and {hist_count} history entries to Supabase.")
    print("=" * 60)

if __name__ == "__main__":
    migrate()
