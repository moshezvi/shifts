# Agent notes — `shifts` repo

Concise instructions for AI assistants and humans automating work here. **Domain decisions and scheduling semantics** live in `docs/shifts-domain.md` — read that file before changing product behavior; avoid duplicating long prose here.

## Stack and layout

- **Backend**: Python + FastAPI under `backend/app/`.
- **Database**: SQLite; default file `data/shifts.db` (gitignored). Override with env **`DATABASE_PATH`** if needed.
- Startup order: load schema → lightweight migrations in `database.py` → seed if empty (`seed.py`).

## Encoding and text

- Treat everything as **UTF-8**. Hebrew names and labels are normal `str` / DB `TEXT`; JSON responses must remain Unicode-safe (`charset=utf-8` on HTTP).

## Domain constants

- **`app/domain.py`** holds small rule sets (`VOLUNTEER_ROLES`, `SWAP_ELIGIBLE_ROLES`, `REGIONS`, etc.). **`schema.sql`** duplicates allowed codes via `CHECK` where applicable — keep them consistent when adding values.
- **Regions**: `IL` | `NA` — **no cross-region pairing** for scheduling unless `docs/shifts-domain.md` says otherwise.
- **Swaps (current)**: eligibility is tied to **`support`**; validate in API when adding endpoints.

## Time and shifts

- Operational boundaries and slot lengths are defined in **`docs/shifts-domain.md`** (anchor **`Asia/Jerusalem`**, 08:00→08:00 operational day, IL→NA handoff rules).
- Implement times as **timezone-aware instants** (store UTC or unambiguous offsets; interpret/display in **`Asia/Jerusalem`**).

## Change discipline

- Prefer **small, focused diffs** aligned with repo conventions.
- When behavior changes, update **`docs/shifts-domain.md`** (and tests/schema) in the same change.
