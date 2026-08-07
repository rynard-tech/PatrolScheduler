# Patrol Scheduler backend

An initial FastAPI/SQLAlchemy/CP-SAT backend for producing a management-reviewed ski-patrol schedule template. Scheduling policy lives in `backend/scheduler`, never in the API. All employee labels in the demo are synthetic.

## Setup

Python 3.12 is required. Direct versions are pinned in `pyproject.toml` and mirrored in `requirements.lock`.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
```

## Database and migrations

For a fresh MVP SQLite database:

```bash
python -c 'from backend.db import initialize_database; initialize_database()'
```

The normalized schema includes seasons, people and qualifications, preferences, waves and patterns, operating configuration, stations and shifts, requirements, families, availability, historical fairness/exposure, assignments, locks, and audited overrides. Alembic is configured for future revision-based upgrades:

```bash
alembic revision --autogenerate -m 'describe change'
alembic upgrade head
```

## Synthetic fixture and CLI demonstration

`backend.fixtures.synthetic_problem()` loads a deterministic, feasible seven-day operation. It includes full-time and part-time patrollers, supervisors, two managers, rookies, qualifications, families, distinct PT availability, historical station counts, specialty shifts, station requirements, patterns, and a hard budget. It does not contain production identities.

```bash
patrol-schedule
# machine-readable output only
patrol-schedule --json-only > schedule.json
```

The output contains every assignment, date/station and date/shift totals, actual and budgeted hours, budget variance, independent validation, and preference/fairness summaries. Run the API with `uvicorn backend.api.app:app`; `POST /demo/schedule` returns the same structured demonstration.

## Spreadsheet import boundary

Import adapters accept configurable source-column mappings and first produce a preview. Raw values are retained beside normalized values. Identity resolution prefers employee number and then exact normalized name. Fuzzy candidates remain `UNRESOLVED` or `AMBIGUOUS`; an administrator must call `confirm_fuzzy_match` and regenerate the preview before commit. Notes remain raw notes and never become constraints automatically.

## Solver stages and hard-rule behavior

The three stages are independent Python services: wave roster selection, work-pattern awards, and daily deployment. Shared hard constraints and soft costs are separate modules. Deployment enforces configured station/qualification minima, specialty counts and distinct specialty supervisors, approved absence, locks, manager/rookie station rules, weekly station diversity, normal four-shift/40-hour limits, the manager five-day exception, and hard budgets. `FIRST_TRACKS` and `NIGHT_SKI` are shift codes while every assignment separately has a station.

Preflight failures and CP-SAT infeasibility return structured conflict codes and possible resolution categories; the service never returns a knowingly broken schedule. An independent validator checks emitted results rather than trusting the optimizer.

## Tests

```bash
pytest
```

Tests cover a complete feasible week, persistence and API startup, explicit fuzzy-match confirmation, qualification and supervisor shortages, overtime, conflicting locks, approved absence, station diversity, and hard-budget conflict.

## Workday boundary

Workday remains the official scheduling and system-of-record product. This application proposes, validates, explains, allows management to lock/override, and eventually exports a clean entry template. It does **not** write to Workday, replace management approval, run payroll, record time, or infer that its generated assignment was actually worked. A schedule becomes official only through the organization's normal reviewed Workday process.
