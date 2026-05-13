# Shifts — domain specification

This document captures **product and scheduling rules** agreed for the project. Update it when decisions change; keep code and tests aligned.

## Purpose

Volunteers work **monthly shifts** (often about once a week). The system should support:

1. Posting a shift that needs **replacement / coverage**.
2. Others proposing **coverage only** or a **swap** (their shift ↔ yours).
3. **Suggestions are optional** until the **originator** (person who opened the request) **approves** one arrangement.
4. **Withdraw** is allowed **until approval**. After approval, the arrangement is **final** in the tool (undo happens outside the app, e.g. via the organizer).
5. After approval, **notify the organizer** (manual channel first — email / Slack webhook / SMS later). Automation may come later.

## Target workflow: monthly scheduling and replacements

The long-term product has two connected workflows:

1. Build and publish the monthly schedule from volunteer availability.
2. Let volunteers resolve conflicts after publication through a replacement /
   swap marketplace.

These concepts should stay separate in the product model:

- **Availability**: a volunteer's stated willingness or ability to work specific
  dates / slots before the monthly schedule is built.
- **Assignment**: the actual published schedule outcome for a shift slot.
- **Replacement request**: an assigned volunteer says they cannot work a
  published shift and asks for coverage and/or a swap.
- **Proposal**: another eligible volunteer offers to cover the shift or swap one
  of their own assigned shifts.
- **Approval**: the originator accepts one proposal; only then should the real
  assignment change.

### Monthly scheduling target

Before each month, volunteers submit availability for the upcoming month
(expected operating cadence: around the 20th of the preceding month).

Availability is scheduling input, not an assignment. The scheduler/admin should
eventually be able to:

1. Review availability by person, week, day, and shift slot.
2. Create a draft monthly schedule from available volunteers.
3. Manually adjust the draft.
4. Publish the schedule when ready.

Later optimization rules may include minimum availability expectations, fair
distribution, weekly coverage goals, and weekend coverage goals. Those rules are
out of scope until explicitly specified.

### Replacement marketplace target

After a schedule is published, an assigned volunteer may open a replacement
request for one of their shifts.

Supported request / proposal paths:

- **Coverage**: another eligible volunteer offers to take the shift.
- **Swap**: another eligible volunteer offers to trade one of their assigned
  shifts for the originator's shift.

For both paths, proposals are optional suggestions until approved by the
originator. The app should not mutate the published schedule when a proposal is
created. Once the originator approves one proposal:

1. The assignment change is applied.
2. Competing proposals are no longer active.
3. The originator, the accepted volunteer, and the admin / organizer are
   notified.
4. The request becomes final in the tool.

## People and attributes

`participant` is the app's local scheduling participant record. Real users may
eventually come from an external roster, identity provider, or another database,
but scheduling tables should still reference the local `participant.id`.

This app owns scheduling facts: availability, assignments, replacement requests,
proposals, approvals, and notification history. An external system may own
identity facts such as login credentials, canonical contact details, or broader
organization membership.

Future roster sync should treat `participant` as a local projection / snapshot
of scheduling-relevant people, likely with fields such as `external_source`,
`external_id`, `synced_at`, and `archived_at`. Historical scheduling records
should remain readable even if a person later disappears from the external
source.

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

### Assignment limit within an operational day

A support volunteer may be assigned to **at most one shift** within a single
operational day (`shift.operational_date`). The same volunteer may be assigned
again on a different operational date.

For bulk updates, validity is based on the final assignment state, not payload
order. Moving a volunteer from one shift to another on the same operational date
is valid when the final state leaves them assigned to only one shift.

## Technical notes (current repo)

- **Backend**: Python (FastAPI), SQLite file DB (default path under repo `data/`, gitignored).
- **Seed**: runs only when there are **no** participants yet; deleting the DB file recreates from scratch.
- **Shift rows**: each row has **`operational_date`** (anchor **D**, Jerusalem **08:00→08:00**), **`region`** (`IL` or `NA`), **`slot_label`**, and **`starts_at` / `ends_at`** stored as **UTC ISO strings**. Slots are generated from `Asia/Jerusalem` rules in `backend/app/schedule.py`; **`python -m db`** (or repeated bootstrap) fills a rolling horizon via **`ensure_shift_slots`**.
- **Week UI / API**: `GET /api/shifts?week_offset=N` returns shifts whose **`operational_date`** falls in the **Jerusalem civil week** Sunday–Saturday containing “today” (offset 0), with **`week_start`** / **`week_end`** in the JSON. Operational dates align with those calendar labels (including overnight NA slots on the same anchor **D**).
- **Long-form truths** live here; **short agent constraints** live in `AGENTS.md` at the repo root.
