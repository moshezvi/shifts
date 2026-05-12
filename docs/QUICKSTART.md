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

## Initialize the database (**required** before first API run)

Provisioning lives in **`db/`** at the repo root. The web app **does not** create or migrate the database; it returns **503** with a hint if the SQLite file is missing.

From **repository root** (venv active, with deps installed as above):

```bash
cd /path/to/shifts   # repo root, parent of backend/ and db/
source backend/.venv/bin/activate   # or your venv location
python -m db
```

`python -m db` adds **`backend/`** to `PYTHONPATH` so `app.*` imports resolve.

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

Fresh database (empty participants → seed runs on next init):

```bash
rm -f data/shifts.db
```

Then run **`python -m db`** (from repo root). Start uvicorn only after the file exists.

## Tests and lint

From **repository root** (install dev deps once: `pip install -r backend/requirements-dev.txt`):

```bash
source backend/.venv/bin/activate
pytest
ruff check backend/app db backend/tests
```

CI (`.github/workflows/ci.yml`) runs **pytest** and **ruff** on push/PR to `main`.

## Optional: synthetic shift assignments (demo data)

From repo root (DB must exist; see **`python -m db`**):

```bash
source backend/.venv/bin/activate
python scripts/randomize_week_assignments.py --dry-run
python scripts/randomize_week_assignments.py
```

Reads **support** volunteers and **shift** rows from SQLite, then picks a random same-region volunteer per slot (`--days` controls how many operational days from today’s anchor; default **7**). `--dry-run` prints without writing; `--seed 42` for reproducible picks; `--only-unassigned` skips filled slots; `--clear-first` clears the whole window then refills.

More demo volunteers (defaults **50** IL + **30** NA support inserts): **`python scripts/seed_random_supporters.py`** (`--dry-run`, `--il` / `--na`).

Full reset for **May 10–23, 2026** (empty shifts + random fills): **`./scripts/rebuild_demo_two_weeks.sh`** from repo root (see **`scripts/README.md`**).

Bulk API: **`PATCH /api/shifts/bulk`** with JSON `{"assignments": [{"shift_id": 1, "assigned_participant_id": 2}, ...]}` (transaction, all-or-nothing).

## Optional env

```bash
export DATABASE_PATH=/path/to/custom.db
```

Run **`uvicorn`** from **`backend/`** so imports resolve (`app.main:app`).
