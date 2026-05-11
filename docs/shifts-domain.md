# Shifts — domain specification

This document captures **product and scheduling rules** agreed for the project. Update it when decisions change; keep code and tests aligned.

## Purpose

Volunteers work **monthly shifts** (often about once a week). The system should support:

1. Posting a shift that needs **replacement / coverage**.
2. Others proposing **coverage only** or a **swap** (their shift ↔ yours).
3. **Suggestions are optional** until the **originator** (person who opened the request) **approves** one arrangement.
4. **Withdraw** is allowed **until approval**. After approval, the arrangement is **final** in the tool (undo happens outside the app, e.g. via the organizer).
5. After approval, **notify the organizer** (manual channel first — email / Slack webhook / SMS later). Automation may come later.

## People and attributes

- **Display names** may be **Hebrew** (UTF-8 end-to-end: files, JSON, SQLite `TEXT`, HTTP `charset=utf-8`).
- **Role** (stored as codes): `support` | `oncall` | `admin`.
  - **Swap/coverage workflow** (current rule): only **`support`** is swap-eligible; extend deliberately if that changes.
- **Gender** (stored as codes): `M` | `F`.
- **Region** (stored as codes): `IL` | `NA`.
  - **Scheduling / pairing**: IL and **NA do not intermingle** (no cross-region swaps or mixed scheduling within the same operational-day roster unless explicitly changed later).

Human-readable labels (e.g. Hebrew role names) belong in the UI, not necessarily in stored codes.

### Hebrew UI terminology (roles)

Use these in UI copy (gender comes from stored **`M` / `F`**):

| Code (`role`) | Male | Female |
|---------------|------|--------|
| `support` | סייע | סייעת |
| `oncall` | כונן | כוננית |
| `admin` | מנהל | מנהלת |

Avoid **משתמשים** for these roles; prefer role-specific terms (above) or neutral **איש/ת צוות** when referring to any volunteer regardless of role.

## Operational “shift day” (Israel time)

The group defines a **single operational day** anchored in **`Asia/Jerusalem`**:

- **Start**: 08:00 local on calendar date **D**
- **End**: 08:00 local on calendar date **D+1**

So each operational day is **24 hours** in **local Israel civil time**, not UTC midnight.

### Within one operational day (conceptual grid)

In order through the evening:

- **Two-hour** slots from **08–10** through **16–18** (i.e. 08–10, 10–12, 12–14, 14–16, 16–18).
- **Exceptions (three-hour blocks)**: **18–21** and **21–24**.

After **local midnight** (still **before** the operational day ends at the next 08:00):

- **Two-hour** overnight slots: **00–02, 02–04, 04–06, 06–08** (still **Asia/Jerusalem**).

### Labeling overnight slots (“previous day”)

Slots after midnight are **labeled with the operational date they belong to** — i.e. the **calendar morning when that operational day started** (the “previous” calendar date relative to the clock right after midnight). Example: times on **D+1** before 08:00 still roll up under **operational date D** in listings.

### IL vs NA handoff within the same operational day

Within that same **08:00→08:00** window:

1. After the **21–24** block and into the **post-midnight** segment, **ownership switches from IL to NA** for the remaining slots until **08:00**.
2. Then the **next** operational day begins again with **IL** leading the **08–10** block.

Exact implementation should use **stored instants (UTC)** plus **`Asia/Jerusalem`** for interpretation and labeling.

## Technical notes (current repo)

- **Backend**: Python (FastAPI), SQLite file DB (default path under repo `data/`, gitignored).
- **Seed**: runs only when there are **no** participants yet; deleting the DB file recreates from scratch.
- **Shift rows**: each row has **`operational_date`** (anchor **D**, Jerusalem **08:00→08:00**), **`region`** (`IL` or `NA`), **`slot_label`**, and **`starts_at` / `ends_at`** stored as **UTC ISO strings**. Slots are generated from `Asia/Jerusalem` rules in `backend/app/schedule.py`; **`python -m db`** (or repeated bootstrap) fills a rolling horizon via **`ensure_shift_slots`**.
- **Long-form truths** live here; **short agent constraints** live in `AGENTS.md` at the repo root.
