# Backlog / TODO

Parking lot for next sessions. Check items off as you go.

## Seed / participants

- [ ] Expand seed data to roughly **30 supporters** in **IL** and **~10** additional supporters in **NA** (order-of-magnitude roster).
- [ ] Keep a deliberate **M/F split** among supporters (document rough ratio in seed comments if helpful).

## Scheduling model

- [ ] Support **multiple supporters assigned to the same shift slot** (schema change: likely a junction table `shift_assignment(shift_id, participant_id, …)` instead of a single `assigned_participant_id` on `shift`, plus API/UI updates).

## Tests

- [ ] Add **unit tests** for core logic (`schedule.py` operational slots, IL/NA bands, `domain.py` helpers, assignment validation).
- [ ] Add **smoke tests** for HTTP API (health, participants, shifts list, PATCH assign, basic UI routes if feasible).
- [ ] Wire tests into **CI** when you have it (GitHub Actions or similar).

## Tooling

- [ ] Add **Ruff** for lint (and optionally format): config file, `requirements-dev.txt` or `[project.optional-dependencies]`, document run command in `AGENTS.md` or README snippet.

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

- [ ] Replace / complement table views with a **calendar experience** (month/week, operational-day boundaries, IL/NA coloring, maybe drag-and-drop once multi-assign exists).
- [ ] Revisit stack then (**Next.js**, **FullCalendar**, or similar) only when requirements are clear — current static pages stay valid until then.

## Nice-to-have (not blocking)

- [ ] Persist “edit mode” preference (optional `sessionStorage`).
- [ ] Broader Hebrew copy review with stakeholders.
