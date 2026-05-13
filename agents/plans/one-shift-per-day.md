# Plan: One shift per volunteer per operational day

Planning-only spec. Do not implement production code from this file until the
user explicitly starts the implementation stage.

## Goal

Enforce the scheduling rule that a support volunteer may be assigned to at most
one shift in a single operational day.

Operational day means the existing `shift.operational_date` anchor: Jerusalem
08:00 on calendar date D through 08:00 on D+1.

## Non-goals

- Do not implement multiple supporters per shift. That is a later schema/API/UI
  stage.
- Do not change the existing slot template, IL/NA handoff, week range, or
  operational date calculation.
- Do not add participant CRUD.
- Do not migrate to a junction table yet.
- Do not add a DB-level uniqueness constraint in this stage unless the user
  explicitly chooses that hardening path.

## Current behavior

- `PATCH /api/shifts/{shift_id}` assigns or unassigns one support volunteer.
- `PATCH /api/shifts/bulk` applies many shift assignment changes in one
  all-or-nothing transaction.
- Shared assignment validation lives in `backend/app/shift_assignment.py`.
- Current validation covers:
  - shift exists,
  - participant exists,
  - participant role is `support`,
  - participant region matches shift region.
- Current validation does not prevent assigning the same participant to multiple
  shift rows with the same `operational_date`.
- The week UI (`frontend/week.html`) assigns a single shift at a time through a
  select control and already surfaces server errors with an alert.

## Product decision

The daily limit applies globally per volunteer and operational date:

- Same `assigned_participant_id`.
- Same `shift.operational_date`.
- Any slot in that operational day.
- Region does not relax the rule. Existing region validation should already
  prevent cross-region assignment.

Allowed:

- Assigning the same volunteer on different operational dates.
- Re-saving the same volunteer on the same shift.
- Unassigning a shift.
- Reassigning a volunteer from one shift to another in the same operational day
  when the final state leaves them assigned to only one shift.

Rejected:

- Assigning a volunteer to a second shift on an operational date where they are
  already assigned to another shift.
- Bulk requests whose final state would assign the same volunteer to multiple
  shifts on the same operational date.

## API behavior

### Single assignment

`PATCH /api/shifts/{shift_id}` should:

1. Keep existing validations.
2. If `assigned_participant_id` is `null`, unassign and return 200.
3. If assigning a participant, check whether another shift row already has:
   - same `operational_date` as the target shift,
   - same `assigned_participant_id`,
   - different `shift.id`.
4. If such a row exists, return HTTP 409 Conflict.
5. Otherwise update and return the existing response shape.

Recommended error detail:

```json
{
  "detail": "participant already assigned on operational_date YYYY-MM-DD"
}
```

Optionally include the conflicting shift id/slot label in the message while
keeping `detail` as a string so the current UI can display it without structural
changes.

### Bulk assignment

`PATCH /api/shifts/bulk` should remain all-or-nothing and should validate the
final state, not the payload order.

Examples:

- Assign participant P to shift A and shift B on the same operational date in
  one request: reject with 409 and rollback all changes.
- Shift A currently has P. Bulk request unassigns A and assigns P to B on the
  same operational date: allow, regardless of item order, because final state is
  valid.
- Shift A currently has P. Bulk request assigns P to B without unassigning A:
  reject with 409 and rollback.

Recommended implementation shape:

1. Begin transaction.
2. Validate shift existence, participant existence, role, and region for every
   item.
3. Apply requested updates inside the transaction without committing.
4. Run a final invariant query for touched participants/dates:
   group by `operational_date, assigned_participant_id` where
   `assigned_participant_id IS NOT NULL`, and reject any count greater than 1.
5. Roll back and return 409 for daily-limit conflicts.
6. Commit only after all validations pass.

This avoids order-dependent behavior in bulk updates.

## UI behavior

Minimum acceptable UI:

- If the server returns 409, show the existing alert with the server detail and
  restore the previous select value.

Preferred UI for this stage:

- In edit mode, disable supporter options that are already assigned to another
  shift on the same operational date.
- Keep the currently selected supporter enabled for their current shift.
- Use the cached week shift data already present in `frontend/week.html`.
- After a successful assignment, update `cacheShifts` as it does today so
  disabled options refresh the next time the grid renders.

Suggested Hebrew copy for disabled options can be short, for example:
`משובץ/ת כבר ביום זה`.

## Code surfaces

Likely files:

- `backend/app/shift_assignment.py`
  - Add the daily-limit validation.
  - Consider a small custom exception type so API handlers can return 409
    without string-matching every `ValueError`.
- `backend/app/main.py`
  - Map daily-limit conflicts to HTTP 409 for both single and bulk endpoints.
- `frontend/week.html`
  - Disable same-day unavailable supporters in edit-mode selects.
  - Continue surfacing server errors.
- `backend/tests/test_api_smoke.py`
  - Add API tests for single and bulk conflict behavior.
  - Update existing bulk success test if it can reuse the same IL supporter.
- `docs/shifts-domain.md`
  - Add the one-shift-per-operational-day rule once implemented.
- `docs/TODO.md`
  - Mark or rewrite the TODO after implementation is complete.

## Tests

Backend tests:

- Single assignment accepts a support volunteer on an empty shift.
- Single assignment rejects the same volunteer on a second shift with the same
  `operational_date` using HTTP 409.
- Single assignment allows the same volunteer on a shift with a different
  `operational_date`.
- Re-saving the same volunteer on the same shift succeeds.
- Unassigning succeeds.
- Bulk assignment rejects two same-day shifts for the same volunteer with HTTP
  409 and rolls back all updates.
- Bulk assignment allows moving a volunteer from shift A to shift B on the same
  operational date when the final state is valid.
- Existing wrong-role, wrong-region, unknown-shift, and atomic rollback tests
  still pass.

UI checks:

- In edit mode, a supporter already assigned elsewhere on the same day is not
  selectable for another shift.
- A server-side conflict still restores the previous select value and displays
  the error.

Verification commands:

```bash
pytest -q
ruff check .
```

## Open questions

- Should the API error detail include the conflicting shift id and slot label?
  Recommendation: yes, as a string, because it helps users and keeps the current
  UI simple.
- Should this rule eventually become a DB-level invariant?
  Recommendation: not in this stage. App-level validation matches the TODO and
  avoids adding a constraint that will be redesigned for the future
  multi-assignment table.
- Should edit mode hide unavailable supporters or show disabled options?
  Recommendation: show disabled options so the user understands why a familiar
  person is unavailable.

## Definition of done

- Single and bulk assignment endpoints enforce the rule.
- Bulk validation is based on final state and remains atomic.
- UI prevents obvious same-day duplicate selections and still handles server
  conflicts.
- Tests cover single, bulk, rollback, and allowed transfer behavior.
- `docs/shifts-domain.md` documents the rule.
- `docs/TODO.md` no longer lists this stage as open.
- `pytest -q` and `ruff check .` pass, or any inability to run them is reported.
