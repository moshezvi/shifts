# Schema roadmap: scheduling and replacement marketplace

Planning-only note. Do not implement schema or production code from this file
until the user explicitly starts an implementation stage.

## Goal

Map the current SQLite schema to the long-term product model in
`docs/shifts-domain.md`:

1. Monthly availability intake.
2. Draft and published schedule assignments.
3. Replacement / swap marketplace after publication.
4. Originator approval before assignment changes.
5. Notifications to the affected volunteers and admin / organizer.

The main design principle is to keep these concepts separate:

- Availability is input.
- Assignment is the schedule outcome.
- Replacement requests and proposals are intent.
- Approval is the transition that mutates real assignments.

## Current schema

Current tables in `db/schema.sql`:

- `participant`
  - Real-ish volunteer record: display name, email, role, gender, region.
  - No lifecycle fields beyond `created_at`; no archive / active status yet.
- `shift`
  - Generated slot rows with `operational_date`, `region`, `slot_label`,
    `sort_order`, `starts_at`, `ends_at`.
  - Current assignment is embedded as `assigned_participant_id`.
  - `UNIQUE (operational_date, slot_label)` means there is one row per slot
    label across the whole operational day. This works today because IL / NA
    slot labels do not collide.
- `coverage_request`
  - Early marketplace table: request against a `shift`, with originator,
    status, approved offer, and timestamps.
- `offer`
  - Early marketplace table: responder, coverage vs swap, optional
    `swap_shift_id`, pending/withdrawn status.

Current application behavior mostly uses `participant`, `shift`, and
`shift.assigned_participant_id`. Marketplace tables exist in schema but do not
yet appear to drive API/UI behavior.

## Pressure points

### Assignment embedded on `shift`

`shift.assigned_participant_id` is simple and good for the current MVP, but it
will strain under:

- multiple supporters per shift slot,
- assignment history,
- draft vs published assignments,
- replacement approvals that should record before/after assignment state,
- auditing who changed what and when.

### Marketplace tables point to `shift`, not assignment records

`coverage_request.shift_id` correctly names the slot needing coverage, but once
assignments are separated, the request should probably point to the specific
assignment being relinquished. Otherwise the system has to infer who owns the
shift from mutable current state.

### Availability has no table yet

The future monthly workflow needs availability as first-class data. This should
not be represented by assigning someone to a shift, nor by opening replacement
requests.

### Participant lifecycle is not explicit

Real users need at least an active/archive story before the schedule becomes
operational. Hard-deleting participants with historical shifts, requests, or
offers will be risky.

## Recommended target entities

This is a conceptual target, not an immediate migration checklist.

### `participant`

Keep as the local scheduling participant table, even if real people eventually
come from another database or identity provider. Other scheduling tables should
reference local `participant.id`, not raw external user IDs.

The separation of ownership should be:

- external roster / identity source owns login identity and possibly canonical
  contact details,
- this app owns scheduling participation, local role/region constraints,
  availability, assignments, replacement history, and notification history.

Potential sync fields:

- `external_source`
- `external_id`
- `synced_at`
- `timezone`
- unique index on `(external_source, external_id)` when both are present

Add lifecycle later:

- `active` or `archived_at`
- optional admin notes / contact fields
- authentication identity only when login is actually introduced

`timezone` should store an optional IANA timezone for display, such as
`Asia/Jerusalem`, `America/New_York`, or `America/Los_Angeles`. It must not
change operational-date logic; canonical scheduling remains anchored in
`Asia/Jerusalem`.

Avoid hard deletes once participants have assignments or marketplace activity.

### `shift`

Keep as the generated time slot table:

- operational date
- region
- slot label / sort order
- UTC start/end instants
- target / required volunteer count for the slot

`shift` should eventually describe the slot, not who is assigned to it.

Future capacity fields:

- `target_volunteers INTEGER NOT NULL DEFAULT 1`
- optionally `min_volunteers INTEGER` and `max_volunteers INTEGER` if policy
  needs a difference between required, ideal, and allowed staffing

Example: overnight slots might target 4 volunteers for `00-02`, 3 for `02-04`,
2 for `04-06`, and 0 or 1 for `06-08` depending on availability / policy.

Potential future cleanup:

- make uniqueness explicitly include `region`:
  `UNIQUE (operational_date, region, slot_label)`

This is clearer even if labels do not currently collide.

### `shift_assignment`

Future table for actual scheduled people:

```sql
shift_assignment (
  id INTEGER PRIMARY KEY,
  shift_id INTEGER NOT NULL REFERENCES shift(id),
  participant_id INTEGER NOT NULL REFERENCES participant(id),
  status TEXT NOT NULL,
  source TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT,
  replaced_by_assignment_id INTEGER REFERENCES shift_assignment(id)
)
```

One shift may have many assignment rows, up to the slot's allowed staffing
policy. The UI should compare assignment count with the shift's target fields to
show states such as underfilled, filled, optional, or overfilled.

Likely `status` values:

- `draft`
- `published`
- `cancelled`
- `replaced`

Likely `source` values:

- `manual`
- `generated`
- `coverage_approval`
- `swap_approval`

Open question: whether draft/published should be a status on each assignment or
belong to a separate schedule/month version. For near-term work, per-assignment
status is simpler. For a stronger monthly workflow, introduce schedule versions.

### `availability_window` or `availability`

Future table for volunteer monthly availability:

```sql
availability (
  id INTEGER PRIMARY KEY,
  participant_id INTEGER NOT NULL REFERENCES participant(id),
  month TEXT NOT NULL,
  shift_id INTEGER REFERENCES shift(id),
  operational_date TEXT,
  slot_label TEXT,
  availability_status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT
)
```

Two possible shapes:

1. Slot-based availability: availability rows reference generated `shift.id`.
2. Pattern/date-based availability: rows store dates / slot labels before shifts
   are generated.

Recommendation: use slot-based availability after shift rows are generated for
the month. It matches the UI and avoids inventing another slot identity.

The availability UI should be participant-context aware:

- start with an explicit participant context (for example, selected user name at
  the top),
- later derive that context from authentication / session state,
- filter available slots by participant region,
- show canonical Israel slot time and optional participant-local time side by
  side.

Likely `availability_status` values:

- `available`
- `unavailable`
- maybe `preferred` later

### `schedule_cycle` or `schedule_version`

Optional but likely useful once monthly scheduling is real:

```sql
schedule_cycle (
  id INTEGER PRIMARY KEY,
  month TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  availability_due_at TEXT,
  published_at TEXT,
  created_at TEXT NOT NULL
)
```

Likely `status` values:

- `collecting_availability`
- `drafting`
- `published`
- `closed`

This gives the admin a monthly object to manage. It can wait until the first
availability/schedule-builder stage.

### `replacement_request`

Rename or replace current `coverage_request` when marketplace work starts.

Future request should point at the assignment being replaced, not only the
shift:

```sql
replacement_request (
  id INTEGER PRIMARY KEY,
  assignment_id INTEGER NOT NULL REFERENCES shift_assignment(id),
  originator_participant_id INTEGER NOT NULL REFERENCES participant(id),
  request_kind TEXT NOT NULL,
  status TEXT NOT NULL,
  approved_proposal_id INTEGER,
  created_at TEXT NOT NULL,
  cancelled_at TEXT,
  approved_at TEXT
)
```

Likely `request_kind` values:

- `coverage`
- `swap`
- `coverage_or_swap`

Likely `status` values:

- `open`
- `approved`
- `cancelled`

### `replacement_proposal`

Rename or replace current `offer`.

```sql
replacement_proposal (
  id INTEGER PRIMARY KEY,
  request_id INTEGER NOT NULL REFERENCES replacement_request(id),
  responder_participant_id INTEGER NOT NULL REFERENCES participant(id),
  proposal_kind TEXT NOT NULL,
  swap_assignment_id INTEGER REFERENCES shift_assignment(id),
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  withdrawn_at TEXT,
  decided_at TEXT
)
```

Likely `proposal_kind` values:

- `coverage`
- `swap`

Likely `status` values:

- `pending`
- `withdrawn`
- `accepted`
- `declined`

When an originator approves one proposal, application code should atomically:

1. Mark the request approved.
2. Mark the accepted proposal accepted.
3. Mark competing proposals declined or inactive.
4. Mutate assignment rows.
5. Queue or log notifications.

### `notification_log`

Future table for manual or automated notification tracking:

```sql
notification_log (
  id INTEGER PRIMARY KEY,
  event_type TEXT NOT NULL,
  participant_id INTEGER REFERENCES participant(id),
  request_id INTEGER REFERENCES replacement_request(id),
  proposal_id INTEGER REFERENCES replacement_proposal(id),
  channel TEXT NOT NULL,
  status TEXT NOT NULL,
  payload_json TEXT,
  created_at TEXT NOT NULL,
  sent_at TEXT
)
```

This can start as a log of "needs manual notification" before email/SMS/Slack is
automated.

## Phased migration path

### Phase 0: current next stage, no schema rewrite

Implement one volunteer per operational day using current
`shift.assigned_participant_id`.

Why:

- It is the current next TODO.
- It can be enforced in application validation.
- It gives useful behavior without blocking on schema design.

Do not add a DB-level uniqueness constraint yet. The later multi-assignment
table will change the constraint shape.

### Phase 1: participant lifecycle

Add participant create/update/archive before real users are operational.

Likely schema change:

- add `archived_at TEXT` or `active INTEGER NOT NULL DEFAULT 1`

Recommendation: prefer `archived_at` for auditability.

### Phase 2: assignment table migration

Introduce `shift_assignment` while preserving API compatibility.

Migration outline:

1. Create `shift_assignment`.
2. Backfill one assignment row for every shift with
   `assigned_participant_id IS NOT NULL`.
3. Update reads/writes to use `shift_assignment`.
4. Keep `shift.assigned_participant_id` temporarily for compatibility or remove
   it in a later rebuild.

Open question: whether to do this before or after multi-assign. Recommendation:
do it as the first step of multi-assign, because it is the required foundation.

### Phase 3: monthly availability and schedule cycle

Add `schedule_cycle` and `availability` once the product is ready to collect
availability for a real month.

Minimum useful workflow:

1. Ensure shift rows exist for the target month.
2. Volunteers submit availability against shift IDs.
3. Admin views availability and creates draft assignments.
4. Admin publishes assignments.

### Phase 4: replacement marketplace

Replace or migrate the current `coverage_request` / `offer` tables into
assignment-oriented request/proposal tables.

Because the existing tables are not yet active product surfaces, the migration
can likely be simple:

- If no real data exists: rebuild/rename to the target tables.
- If real data exists: migrate requests from `shift_id` to the current
  assignment for that shift, with manual review for ambiguous cases.

### Phase 5: notification log

Add `notification_log` when approval exists.

Start with manual status tracking:

- who should be notified,
- about which approval event,
- whether the notification was sent.

Automated integrations can use the same log later.

## Constraints and invariants to preserve

- Store time as UTC instants or unambiguous offsets.
- Interpret operational dates in `Asia/Jerusalem`.
- Preserve region matching: participants and assigned shifts must stay in the
  same region unless the domain doc changes.
- Preserve support-only assignment for now.
- Keep approval atomic: request/proposal status changes and assignment mutation
  must commit or roll back together.
- Avoid hard deletes for participants or assignments once they have historical
  schedule or marketplace activity.

## Near-term recommendation

Do not redesign the full schema before the next implementation stage.

Recommended next steps:

1. Finish one-shift-per-operational-day validation on the current schema.
2. Add participant archive/create/update planning or implementation.
3. Use the first multi-assign stage as the moment to introduce
   `shift_assignment`.
4. Defer availability, schedule cycles, and marketplace table rewrites until
   those product stages begin.

This keeps the project moving while still leaving a clear path toward the full
monthly scheduling and replacement marketplace model.
