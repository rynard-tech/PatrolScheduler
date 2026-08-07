# PatrolScheduler

An initial, backend-first implementation of the ski-patrol scheduling engine. It
contains normalized domain models, explicit spreadsheet mapping/validation, a
CP-SAT weekly deployment solver, synthetic fixtures, and JSON/table CLI output.

```bash
python -m pip install -e '.[dev]'
patrol-scheduler demo --json schedule.json
pytest
```

The demo is synthetic. Staffing requirements, shifts, stations, qualifications,
weights, dates, employee counts, and employee identities are all input data.
An infeasible solve returns a structured conflict report and never a partially
valid schedule.
