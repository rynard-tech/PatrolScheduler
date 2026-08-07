# PatrolScheduler backend MVP

This phase contains normalized synthetic scheduling models, a configurable fixture generator,
a CP-SAT work-pattern/staffing-wave solver, explicit validation/conflict/shortage results, and a
backend-only demonstration CLI.

## Run the synthetic week

```bash
python -m patrol_scheduler.cli
```

When running directly from a checkout, set `PYTHONPATH=backend`, or install the project first
with `python -m pip install -e .`. The command emits structured JSON followed by a readable
seven-day table. Use `--json-only`, `--employees`, and `--target` to configure the demonstration.

## Test

```bash
python -m pytest
```
