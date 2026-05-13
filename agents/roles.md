# Agent roles

This folder is the source of truth for agent operating rules in this repo.
`AGENTS.md` is the entry point. Tool-specific files, such as Cursor `.mdc`
rules, should point here instead of duplicating long policy.

The roles below are responsibilities, not separate runtime processes. One
assistant may wear several hats in one turn, but it should say which mode it is
using when that affects scope.

## Default operating model

1. Read `AGENTS.md` first.
2. For non-trivial work, skim `docs/TODO.md` and `docs/shifts-domain.md`.
3. If product behavior is unclear, write or update a mini-spec before
   implementation.
4. Keep code changes focused and tied to documented behavior.
5. When a stage is complete or ready to push, run the planning steward and gap
   reviewer passes before handing off.

## Planning-only mode

Use this mode when the user asks to plan, design, scope, create a spec, or avoid
writing implementation code.

Planning artifacts live in `agents/plans/`. Prefer one focused file per stage,
named after the work rather than the date.

Allowed outputs:

- Acceptance criteria.
- Open questions and product decisions.
- Implementation sequence.
- Test plan.
- Documentation-only updates, if requested or useful.

Avoid in planning-only mode:

- Production code edits.
- Schema migrations.
- Test implementation.
- Refactors.

If a planning-only pass reveals an urgent inconsistency, document it as an open
question or captured gap instead of fixing it silently.

## Product / Domain Steward

Owns scheduling semantics and product truth.

Responsibilities:

- Keep `docs/shifts-domain.md` accurate.
- Define acceptance criteria for scheduling behavior.
- Check operational-day logic: `Asia/Jerusalem`, 08:00 to 08:00, and overnight
  slot labeling.
- Check region rules: `IL` and `NA` do not intermingle unless the domain doc
  says otherwise.
- Check role rules: `support`, `oncall`, `admin`, swap eligibility, and Hebrew
  UI terminology.
- Catch domain contradictions before implementation starts.

Outputs:

- Domain decisions in `docs/shifts-domain.md`.
- Acceptance criteria in a plan or TODO item.
- Explicit open questions when a product choice is missing.

## Planning Steward

Owns backlog accuracy and stage shape.

Responsibilities:

- Keep `docs/TODO.md` aligned with actual project state.
- Identify the next coherent unit of work.
- Maintain stage definitions and definitions of done.
- Update TODO lines when work is completed, superseded, or narrowed.
- Keep the planned-work summary in `AGENTS.md` honest.

Before non-trivial work:

- Skim `docs/TODO.md` and `docs/shifts-domain.md`.

When finishing a task:

- In `docs/TODO.md`, mark completed work, delete obsolete bullets, or rewrite
  items that changed scope.
- Update `docs/shifts-domain.md`, `docs/QUICKSTART.md`, or
  `scripts/README.md` when behavior, API, scripts, setup, or operator flow
  changed.
- Update the planned-work sentence in `AGENTS.md` if it no longer matches
  `docs/TODO.md`.

Scope:

- Do not add speculative tasks to the main sections of `docs/TODO.md` unless
  the user asks.
- The `Captured gaps (auto)` subsection is maintained by the Gap Reviewer.

Outputs:

- Updated `docs/TODO.md`.
- Stage plans and definitions of done.
- Documentation updates when commands, behavior, or operator flow changes.

## Implementation Agent

Owns code changes after intent is clear.

Responsibilities:

- Make backend, frontend, DB, and script changes that match the current spec.
- Prefer existing repo patterns over new abstractions.
- Keep domain constants in sync across `backend/app/domain.py` and
  `db/schema.sql`.
- Avoid inventing product behavior silently.
- Preserve unrelated local changes.

Before implementation:

- Confirm there is a TODO, issue, mini-spec, or explicit user request.
- Identify affected surfaces: API, UI, DB, scripts, docs, tests.

Outputs:

- Focused code diffs.
- Updated tests and docs when behavior changes.
- Verification commands and results.

## Test / Verification Agent

Owns evidence that the intended behavior works.

Responsibilities:

- Translate acceptance criteria into tests.
- Review existing test coverage before adding new tests.
- Cover API behavior, scheduling rules, DB bootstrap/migrations, scripts, and UI
  behavior as appropriate.
- Run relevant verification commands before final handoff when feasible.

Expected checks for this repo:

- `pytest` for backend and DB behavior.
- `ruff check .` for Python style.
- Browser/UI checks when changing the static frontend.

Outputs:

- Test files or review notes.
- Verification summary with commands run.
- Residual risk when something could not be tested.

## Gap Reviewer

Owns coherence across product surfaces.

Responsibilities:

- Look for missing CRUD/lifecycle stories for exposed entities.
- Check API and UI parity.
- Check domain alignment for scheduling, regions, roles, and operational dates.
- Check failure, validation, and empty states.

Output:

- List concrete gaps in the reply.
- If a specific, actionable gap is not already covered in `docs/TODO.md`, append
  one non-duplicate `- [ ]` line under `## Captured gaps (auto)`.
- Do not flood the backlog with vague ideas.

## Release / Stage Completion Agent

Runs when the user says a stage is complete, ready to commit, ready to push,
shipping, PR-ready, or similar.

Planning steward pass:

- Re-read `docs/TODO.md` against what shipped.
- Mark done, delete, or rewrite stale TODO lines.
- Update `docs/shifts-domain.md`, `docs/QUICKSTART.md`, `scripts/README.md`,
  and `AGENTS.md` when readers would otherwise be misled.

Gap reviewer pass:

- Run a short coherence check across CRUD/API/UI/domain/edge cases.
- List remaining gaps in the reply.
- Add new non-duplicate captured gaps to `docs/TODO.md`.
- Check off or remove captured gaps that the stage resolved.

Release handoff:

- Check `git status`.
- Run or report the relevant verification commands.
- Produce a commit-ready summary with changed files, verification, and remaining
  risk.
