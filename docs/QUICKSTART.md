# Quickstart — local development

## Prerequisites

- Python **3.11+** recommended (stdlib **`zoneinfo`** used for `Asia/Jerusalem`).
- Repo root is the parent of **`backend/`** and **`data/`** (default SQLite path).

## First-time setup

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the API + UI (development)

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open:

| URL | What |
|-----|------|
| http://127.0.0.1:8000/ui | Week view (HTML) |
| http://127.0.0.1:8000/ui/by-user | By person |
| http://127.0.0.1:8000/docs | OpenAPI / try API |

Stop the server: **Ctrl+C** in that terminal.

If you run uvicorn **in the background**, stop it with:

```bash
pkill -f "uvicorn app.main:app"
```

## Database

- Default file: **`data/shifts.db`** (under repo root; gitignored).
- Override path: **`DATABASE_PATH`** env var (absolute path recommended).

Fresh database (empty participants → seed runs on startup):

```bash
rm -f data/shifts.db
```

Then restart uvicorn so migrations + seed + shift slots run again.

## Optional env

```bash
export DATABASE_PATH=/path/to/custom.db
```

Run **`uvicorn`** from **`backend/`** so imports resolve (`app.main:app`).
