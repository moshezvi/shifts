# Agent notes — `shifts` repo

Concise instructions for AI assistants and humans automating work here. **Domain decisions and scheduling semantics** live in `docs/shifts-domain.md` — read that file before changing product behavior; avoid duplicating long prose here.

**Planned work** is tracked in **`docs/TODO.md`** (multi-assign shifts, participant CRUD gap, `domain.py` tests; week grid + bulk assign + dev scripts largely done).

**Planning steward:** When you complete work that matches or closes an item in **`docs/TODO.md`**, treat backlog hygiene as part of the same change: check off or remove the item, and update **`docs/shifts-domain.md`**, **`docs/QUICKSTART.md`**, or **`scripts/README.md`** if behavior or commands changed. When picking up multi-step work, skim **`docs/TODO.md`** and **`docs/shifts-domain.md`** first. Details: **`.cursor/rules/planning-steward.mdc`**.

**Gap reviewer:** Question whether the product stays **coherent** (CRUD symmetry, API vs UI parity, domain invariants). Surface gaps in replies **and** append concrete items under **`docs/TODO.md`** section **`Captured gaps (auto)`** when appropriate—see **`.cursor/rules/logical-gaps.mdc`**. Rules apply **per Agent chat** (when Cursor loads project rules), not on a timer.

**Stage complete (pre-push):** When the user says a **stage is done** and they are **ready to commit and push** (or equivalent—see *Stage complete* below), run **both** the planning steward and gap reviewer passes in **the same turn**: update repo files (`docs/TODO.md`, domain/quickstart/scripts, `AGENTS.md` blurb, `Captured gaps`) as needed—not only a verbal summary.

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

## Planning steward (backlog + docs)

Act as the **planning steward** for this repo alongside feature work:

- **Before** a non-trivial change: skim **`docs/TODO.md`** and **`docs/shifts-domain.md`** so work matches stated direction.
- **After** completing something that fulfills or supersedes a TODO line: update **`docs/TODO.md`** (`[x]` done items you leave for history, or delete lines that are obsolete; adjust wording if scope changed).
- **After** user-visible or operator-visible changes: update **`docs/shifts-domain.md`**, **`docs/QUICKSTART.md`**, and/or **`scripts/README.md`** in the same session when appropriate.
- **Keep `AGENTS.md` honest**: if the one-line TODO summary at the top no longer matches `docs/TODO.md`, fix that sentence.

Do not add speculative tasks to the **main** sections of `docs/TODO.md` without the user asking; the job is **maintenance and accuracy**, not roadmap invention. **Exception:** the **Captured gaps (auto)** subsection is maintained by the **gap reviewer** rule—merge or retire those lines when you ship fixes.

## Consistency and gap reviewer

Act as a **gap reviewer** alongside implementation and review:

- **Entity lifecycle**: If the system models **users/participants** (or similar) with IDs shown in UI/API, expect a **deliberate story** for add / edit / archive or delete — or an explicit product decision that only seed/scripts manage them. Flag “read-only people” as a gap unless documented.
- **API vs UI**: New server capabilities should have a **clear path** in the UI (or be documented as API-only); new UI affordances should not depend on missing endpoints without calling it out.
- **Domain alignment**: Cross-check **`docs/shifts-domain.md`** (regions, roles, operational week vs anchor) when behavior touches scheduling.
- **Failure and empty states**: Consider permission errors, validation, and “no rows” for list endpoints and scripts.

**Output**: State gaps in the conversation (short bullets). **Also** append warranted, non-duplicate `- [ ]` lines under **`## Captured gaps (auto)`** in **`docs/TODO.md`** (create the section if missing)—see **`.cursor/rules/logical-gaps.mdc`** for deduping and scope. Other sections of `docs/TODO.md` stay for human/planning steward edits unless a gap clearly belongs there.

## Stage complete (pre-commit / pre-push)

When the user announces that a **stage or milestone is complete** and they are **ready to commit and push** the code, treat that as an explicit signal to **update documentation and backlog in-repo** in the **same response** (edits to tracked files), not only advice.

**Typical phrases** (non-exhaustive): *stage complete*, *ready to commit*, *ready to push*, *shipping this*, *milestone done*, *PR is ready*, *going to push*.

**Planning steward (must do):**

1. Re-read **`docs/TODO.md`** against what was built: **`[x]`**, **delete**, or **rewrite** lines that this stage fulfilled or made obsolete (all sections, including tightening **`## Captured gaps (auto)`** if this stage fixed an item there).
2. Update **`docs/shifts-domain.md`**, **`docs/QUICKSTART.md`**, and/or **`scripts/README.md`** if behavior, API, scripts, or operator steps changed and readers would be wrong otherwise.
3. If the opening **planned work** sentence in **`AGENTS.md`** no longer matches `docs/TODO.md`, fix it.

**Gap reviewer (must do):**

1. Short **coherence pass** on what shipped (CRUD/API/UI/domain/edges)—list any **remaining** gaps in the reply.
2. **`docs/TODO.md` → `## Captured gaps (auto)`**: append **non-duplicate** `- [ ]` items for **new** gaps this stage exposed; **check off or remove** lines that this stage **resolved**.

If nothing needs changing, say so explicitly (e.g. “TODO and docs already match this stage”) after re-reading the files.

## Change discipline

- Prefer **small, focused diffs** aligned with repo conventions.
- When behavior changes, update **`docs/shifts-domain.md`** (and tests/schema) in the same change.
