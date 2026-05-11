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

## Nice-to-have (not blocking)

- [ ] Persist “edit mode” preference (optional `sessionStorage`).
- [ ] Broader Hebrew copy review with stakeholders.
