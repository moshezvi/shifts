# Backlog / TODO

Parking lot for next sessions. When you **complete** something listed here (or supersede it), update this file and related docs per **`AGENTS.md`** → *Planning steward* and **`.cursor/rules/planning-steward.mdc`**. The **gap reviewer** may append new bullets under **Captured gaps (auto)** on its own (see **`.cursor/rules/logical-gaps.mdc`**). When you announce a **stage complete** / **ready to commit and push**, both roles should refresh this file and other docs in the **same** change—see **`AGENTS.md` → *Stage complete***.

## Seed / participants

- [x] Large **synthetic** roster path: **`scripts/seed_random_supporters.py`** (defaults 50 IL / 30 NA, Hebrew names, **`--replace-synth`**). Optional: fold similar sizes into **`db` seed** if every fresh DB should start big without running the script.
- [ ] Keep a deliberate **M/F split** among supporters (document rough ratio in seed comments if helpful).

## Scheduling model

- [ ] Support **multiple supporters assigned to the same shift slot** (schema change: likely a junction table `shift_assignment(shift_id, participant_id, …)` instead of a single `assigned_participant_id` on `shift`, plus API/UI updates).

## Tests

- [x] **Unit tests** for `schedule.py` (operational slots, IL/NA, anchor dates).
- [x] **Smoke tests** for HTTP API (`/health`, `/api/participants`, `/api/shifts`, `/ui`).
- [x] **GitHub Actions** workflow (pytest + ruff on push/PR).
- [x] Tests for **`PATCH /api/shifts`** (single assign) and **`PATCH /api/shifts/bulk`** (success, 404, atomic rollback).
- [ ] Add tests for **`domain.py`** helpers.

## Tooling

- [x] **Ruff** in `pyproject.toml` + `backend/requirements-dev.txt`; run `ruff check …` (see QUICKSTART).
- [ ] Optional: `ruff format`, stricter rules, or pre-commit hook.

## Hosting / production (review next)

Shortlist to compare when you’re ready to deploy (FastAPI + SQLite file **or** Postgres later; static UI may stay same-origin or move to **Vercel**):

| Area | Options to evaluate |
|------|---------------------|
| **All-in-one PaaS** | Railway, Render, Fly.io, DigitalOcean App Platform |
| **Frontend-only CDN** | Vercel, Netlify, Cloudflare Pages (API + DB stay elsewhere) |
| **VPS / DIY** | DigitalOcean Droplet, AWS Lightsail, Hetzner — more control, more ops |
| **Managed DB** (if leaving SQLite) | Neon, Supabase, RDS, Fly Postgres |

- [ ] Pick **one** target for v1: usually **single long‑running service** + **persistent disk** if SQLite, or **Postgres** add-on.
- [ ] Decide **same origin** (one host serves `/ui` + `/api`) vs **split** (Vercel + API URL + CORS).
- [ ] Document chosen host + deploy steps in-repo when decided.

## Phase 2 — richer calendar UI

- [x] **Week grid** on **`/ui`**: columns = Jerusalem **Sun–Sat** week (`week_offset` query param), rows = slot template; prev/next week navigation. API: **`GET /api/shifts?week_offset=`** with **`week_start` / `week_end`** metadata.
- [ ] Month-style calendar, richer visuals, drag-and-drop once multi-assign exists.
- [ ] Revisit stack then (**Next.js**, **FullCalendar**, or similar) only when requirements are clear — current static pages stay valid until then.

## Nice-to-have (not blocking)

- [ ] Persist “edit mode” preference (optional `sessionStorage`).
- [ ] Broader Hebrew copy review with stakeholders.

## Captured gaps (auto)

The **gap reviewer** (`.cursor/rules/logical-gaps.mdc`) may append `- [ ]` lines here when it spots a **concrete** product hole during work—no separate ask from a human required. **Planning steward**: dedupe, reword, move, or check off when fixed; keep this section.

- [ ] **Participant lifecycle**: HTTP API (and optionally UI) to **create / update / delete** participants—or document that roster changes are **seed/scripts only**. Today: list + assign shifts, no participant CRUD.
