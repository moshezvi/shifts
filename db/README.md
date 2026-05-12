# Database bootstrap (`db/`)

This directory holds **creation, DDL, and migration** for the SQLite file the app uses. It lives **outside** `backend/app/` so swapping for another database or an existing external store is clearer.

- **`schema.sql`** — SQLite DDL (`CREATE TABLE` / indexes). Applied by **`db.migrations.apply_ddl`**.
- **`migrations.py`** — **`apply_migrations`** (incremental fixes / legacy rebuilds). Keep in sync with **`schema.sql`** when tables change.
- **`bootstrap.py`** — **`init_database(conn)`** (DDL → migrations → seed-if-empty → shift horizon). Opens/creates the DB file via **`create_bootstrap_connection()`** (not `app.database.connect`, which **refuses** a missing file). Optional **`operational_date_range=(first, last)`** inserts slots for that inclusive operational range instead of the rolling horizon from “now”.
- **`python -m db`** — run from **repository root**; see **`docs/QUICKSTART.md`**.

**`backend/app/database.py`** only resolves **`database_path()`**, **`connect()`** (existing file only), and small read helpers — **no** DDL or migrations.
