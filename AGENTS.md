# Agent notes — `shifts` repo

Concise instructions for AI assistants and humans automating work here. **Domain decisions and scheduling semantics** live in `docs/shifts-domain.md` — read that file before changing product behavior; avoid duplicating long prose here.

**Planned work** is tracked in **`docs/TODO.md`** (seed scale-up, multi-assignee shifts; tests/Ruff largely done).

**Local run / restart:** **`docs/QUICKSTART.md`** (venv, `python -m db`, `uvicorn`, tests, ruff).

## Stack and layout

- **Backend**: Python + FastAPI under `backend/app/`.
- **Database**: SQLite file at `data/shifts.db` by default (`DATABASE_PATH` overrides). **`app.database.connect()`** opens an **existing** file only — no DDL/migrations. If the file is missing, the API returns **503** with a hint to run **`python -m db`** from the repo root.
- **Provisioning**: top-level **`db/`** — `schema.sql`, `migrations.py`, `bootstrap.py`. Run **`python -m db`** before (or after) deploy when schema/seed/slots need updating.

## Encoding and text

- Treat everything as **UTF-8**. Hebrew names and labels are normal `str` / DB `TEXT`; JSON responses must remain Unicode-safe (`charset=utf-8` on HTTP).
- Hebrew **role** wording in the UI is defined in **`docs/shifts-domain.md`** (סייע/סייעת, כונן/כוננית, מנהל/מנהלת); use **`frontend/static/role-labels.js`** for dropdown copy.

## Domain constants

- **`app/domain.py`** holds small rule sets (`VOLUNTEER_ROLES`, `SWAP_ELIGIBLE_ROLES`, `REGIONS`, etc.). **`db/schema.sql`** duplicates allowed codes via `CHECK` where applicable — keep them consistent when adding values.
- **Regions**: `IL` | `NA` — **no cross-region pairing** for scheduling unless `docs/shifts-domain.md` says otherwise.
- **Swaps (current)**: eligibility is tied to **`support`**; validate in API when adding endpoints.

## Time and shifts

- Operational boundaries and slot lengths are defined in **`docs/shifts-domain.md`** (anchor **`Asia/Jerusalem`**, 08:00→08:00 operational day, IL→NA handoff rules).
- **`backend/app/schedule.py`** generates slot specs and fills **`shift`** rows (`operational_date`, `region`, `slot_label`, UTC **`starts_at`/`ends_at`**).
- Implement times as **timezone-aware instants** (store UTC or unambiguous offsets; interpret/display in **`Asia/Jerusalem`**).

## Change discipline

- Prefer **small, focused diffs** aligned with repo conventions.
- When behavior changes, update **`docs/shifts-domain.md`** (and tests/schema) in the same change.
