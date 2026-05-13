# Plan: MVP demo readiness

Planning-only note. Do not implement production code from this file until the
user explicitly starts an implementation stage.

## Goal

Prepare the app for a credible MVP demo with real-world volunteer coordinators
or potential client organizations.

The demo does not need every long-term feature. It should prove that the core
scheduling model is understandable, time handling is trustworthy, and admins can
operate the schedule without breaking domain rules.

## Product MVP

Minimum product capabilities for a credible demo:

- Real participant management:
  - create participants,
  - edit participant details,
  - archive participants instead of hard-delete.
- Clear week/month schedule navigation:
  - current week is obvious,
  - non-current `week_offset` is obvious,
  - return-to-current-week state is clear.
- Admin assignment workflow:
  - assign and unassign support volunteers,
  - enforce same-region assignment,
  - enforce support-only assignment,
  - enforce at most one shift per volunteer per operational day.
- Availability intake:
  - participant-context-aware page, initially with selected/current participant
    name at the top,
  - week or month view,
  - region-filtered eligible shifts,
  - Israel canonical time plus optional participant-local time.
- Basic export/share surface:
  - printable schedule, copyable table, CSV, or similar admin-friendly output.
- Hebrew copy pass:
  - role labels,
  - empty states,
  - error messages,
  - admin/user-facing terms.

Defer unless it is the demo's central pitch:

- full replacement marketplace,
- automated notifications,
- automatic schedule optimization,
- multi-organization support.

If replacement marketplace is demoed, keep it thin:

1. Originator posts a coverage/swap request.
2. Another volunteer proposes coverage or swap.
3. Originator approves.
4. The app shows the intended assignment change and notification targets.

## Operational MVP

Before real volunteers or coordinators touch the app:

- Participant archive story is explicit; avoid hard deletes for historical data.
- Dangerous demo scripts are not exposed through production UI.
- Demo data and real data are separated.
- Empty states are understandable:
  - no shifts,
  - no participants,
  - no available volunteers,
  - no availability submitted.
- Validation errors are clear enough for admins to recover.
- DB backup and restore process exists and has been tested.
- Admin can recover from common mistakes:
  - wrong assignment,
  - bad generated shifts,
  - participant entered incorrectly.
- Optional but useful: assignment audit trail showing who changed an assignment
  and when.

## Deployment MVP

Recommended first production shape:

- One FastAPI service serving both `/api` and `/ui`.
- HTTPS-only public URL.
- Admin auth before any write endpoint is exposed publicly.
- Environment-driven configuration:
  - database path or database URL,
  - app environment,
  - secrets outside git.

Database decision:

- SQLite is acceptable for a tiny demo only if the platform provides persistent
  disk and single-instance deployment.
- Use Postgres if concurrency, durability, multi-instance hosting, or easier
  managed backups matter.

Build and runtime:

- Add a Dockerfile or chosen platform build config.
- Run production ASGI reliably, either through platform-managed uvicorn or a
  process manager such as gunicorn with uvicorn workers.
- Keep static UI same-origin unless a split frontend becomes valuable.

CI/CD:

- Run `pytest`.
- Run `ruff check`.
- Deploy only after green checks.
- Keep dev/demo scripts out of automatic production startup.

Database operations:

- Document bootstrap/migration command.
- Ensure seed/demo data cannot overwrite real participants accidentally.
- Back up before migrations.
- Document restore steps.

Observability:

- Keep `/health`.
- Capture server logs.
- Make app errors visible enough to debug a demo.

Security basics:

- HTTPS.
- Admin authentication / authorization for writes.
- Locked-down CORS if frontend and API split.
- No anonymous destructive endpoints.
- Secrets and credentials outside repository files.

## Recommended implementation order

1. Participant CRUD/archive.
2. Availability intake MVP with participant context and timezone display.
3. Admin schedule builder using availability.
4. Week/month UI clarity and printable/exportable schedule.
5. Admin auth and write-protection.
6. Deployment target decision: SQLite with persistent disk vs Postgres.
7. Deployment config, backup/restore docs, and CI/CD.
8. Optional thin replacement marketplace demo.

## Definition of done for demo readiness

- A coordinator can manage real participants.
- Volunteers or admins can submit availability without changing assignments.
- Admins can build/edit a schedule while domain rules are enforced.
- Time display is trustworthy: canonical `Asia/Jerusalem` plus optional local
  time, with operational dates unchanged.
- The app is reachable over HTTPS.
- Write paths are protected.
- There is a documented backup/restore path.
- Tests and lint pass in CI.
- Demo data can be loaded without risking real data.
