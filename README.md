# CivicSense v4 — Advanced AR + Smart City Prototype (with Supabase Cloud Database)

CivicSense is an educational smart-city prototype for reporting, mapping, managing and tracking civic issues such as potholes, garbage, drainage, street-light faults and water leakage.

---

## 🚀 Key Modules
- **Citizen Report Portal**: Photo evidence upload, OpenStreetMap interactive pin, auto-routing.
- **AR Civic Scan (`/ar`)**: Live camera HUD, evidence capture, GPS geotag, and heading sensor.
- **Cloud Database Support (Supabase)**: Real-time PostgreSQL cloud backend, storage bucket integration, with seamless local SQLite offline fallback.
- **Duplicate Complaint Prevention**: Real-time Haversine distance spatial checking.
- **Municipality Command Center (`/admin`)**: Interactive map, live status badge, severity prioritization, staff assignment, and audit notes.
- **Citizen Tracking (`/track`)**: Live status tracker with auto-refresh and resolution timeline.
- **PDF & CSV Export**: Official downloadable PDF complaint receipt and citywide CSV export.
- **Big Data Lab (`/dataset`)**: 82,000-row synthetic smart-city dataset for analytics demonstration.

---

## ☁️ Supabase Cloud Database Setup Guide

CivicSense is configured to work with **Supabase Cloud PostgreSQL & Storage**. If Supabase credentials are not provided, it runs locally on **SQLite** automatically.

### Step 1: Create a Supabase Project
1. Log in to [Supabase](https://supabase.com) and click **"New project"**.
2. Give your project a name and choose a database password.

### Step 2: Run the Schema in SQL Editor
1. In your Supabase project dashboard, click on **SQL Editor** in the left sidebar.
2. Open [`supabase_schema.sql`](./supabase_schema.sql) from this project folder.
3. Paste the contents into the SQL Editor and click **Run**.
4. This creates:
   - `issues` table (with coordinates, department, status, severity, image URL)
   - `status_history` table (audit timeline)
   - Performance and spatial indexes
   - Row Level Security (RLS) policies for civic reporting
   - `civicsense-uploads` storage bucket for evidence photos

### Step 3: Configure Environment Variables
1. In Supabase, go to **Project Settings -> API**.
2. Copy your **Project URL** and **API Key** (`anon` public key or `service_role` key).
3. In this project folder, edit [`.env`](./.env):

```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-supabase-api-key
SUPABASE_BUCKET=civicsense-uploads
DB_MODE=auto
```

### Step 4 (Optional): Migrate Local SQLite Data to Supabase
If you already have complaints saved locally in `civic.db`, transfer them to Supabase in one step:

```powershell
python tools/migrate_to_supabase.py
```

---

## 💻 Run on Windows / VS Code

```powershell
# 1. Activate virtual environment
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

# 2. Install requirements
python -m pip install -r requirements.txt

# 3. Start the CivicSense server
python -m uvicorn main:app --reload
```

Or simply double-click `start.bat`.

---

## 🌐 Application URLs
- **Citizen Portal**: http://127.0.0.1:8000
- **AR Scan**: http://127.0.0.1:8000/ar
- **Track Complaint**: http://127.0.0.1:8000/track
- **Municipality Console**: http://127.0.0.1:8000/admin
- **Database Status**: http://127.0.0.1:8000/api/db/status
- **Data Lab**: http://127.0.0.1:8000/dataset
- **API Swagger Docs**: http://127.0.0.1:8000/docs
