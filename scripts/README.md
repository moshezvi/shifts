# Dev scripts

Run from the **repository root** unless noted. Use `backend/.venv` and ensure the DB exists (`python -m db`).

## Which script should I use?

| Goal | Command |
|------|---------|
| Normal non-destructive DB init / migration | `python -m db` |
| Clear broken shifts but keep participants | `python scripts/clear_shifts.py --yes --reinitialize` |
| Fill existing shifts with fake assignments | `python scripts/randomize_week_assignments.py --week-offset 0 --clear-first` |
| Add synthetic support volunteers | `python scripts/seed_random_supporters.py` |
| Full destructive demo reset, including participants | `./scripts/rebuild_demo_two_weeks.sh` |
| Lower-level fixed-date demo DB init | `python scripts/rebuild_two_weeks_db.py --start YYYY-MM-DD --end YYYY-MM-DD` |

## `randomize_week_assignments.py`

Fills shift slots with **random support volunteers** (IL shifts → IL support, NA → NA), reading participants and shifts from SQLite.
Within an operational day, each volunteer is picked at most once.

```bash
source backend/.venv/bin/activate
export DATABASE_PATH=/abs/path/to/shifts.db   # optional
python scripts/randomize_week_assignments.py --dry-run --seed 1
python scripts/randomize_week_assignments.py --days 14 --clear-first
python scripts/randomize_week_assignments.py --week-offset 0 --clear-first
python scripts/randomize_week_assignments.py --start-date 2026-05-10 --end-date 2026-05-23 --clear-first
```

Only **`role = support`** can be assigned (same rules as the API). Oncall/admin rows are left in the DB but not used as assignees.

## `seed_random_supporters.py`

Appends extra **support** rows (defaults: **50** IL, **30** NA). Display names are random
**Hebrew** שם + משפחה; emails stay unique each run (batch token). Safe to re-run.

**``--replace-synth``** — delete all earlier script-generated supporters (synth emails /
``Demo Support%`` names), unassign their shifts, remove related coverage rows, then
insert a fresh batch in one transaction:

```bash
python scripts/seed_random_supporters.py --dry-run
python scripts/seed_random_supporters.py
python scripts/seed_random_supporters.py --il 60 --na 40 --seed 7
python scripts/seed_random_supporters.py --replace-synth
```

## `clear_shifts.py`

Nuclear shift reset that **preserves participants**. It deletes shift-family
rows (`offer`, `coverage_request`, `shift`) and can optionally recreate empty
shift rows through the normal bootstrap path.

```bash
python scripts/clear_shifts.py --dry-run
python scripts/clear_shifts.py --yes
python scripts/clear_shifts.py --yes --reinitialize
```

Use **`--reinitialize`** when you want to clear broken shifts/assignments and
immediately refill the default rolling shift horizon. Existing participants stay
in place because the seed runs only when the participant table is empty.

## `rebuild_demo_two_weeks.sh`

One-shot demo reset: stops **uvicorn** for `app.main:app`, deletes the DB file, recreates schema + seed + **empty** shifts for operational dates **2026-05-10 … 2026-05-23** (two calendar weeks), then runs **`randomize_week_assignments.py`** for that same window.

```bash
chmod +x scripts/rebuild_demo_two_weeks.sh   # once
./scripts/rebuild_demo_two_weeks.sh
```

Lower-level pieces (same defaults): **`scripts/rebuild_two_weeks_db.py`** (DB + empty shifts only) and **`randomize_week_assignments.py --start-date … --end-date …`**. Override dates with **`rebuild_two_weeks_db.py --start YYYY-MM-DD --end YYYY-MM-DD`** and matching flags on the randomize step.
