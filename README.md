# Patrol Scheduler

The current MVP is a backend-first, constraint-based weekly deployment generator. It keeps shift, station, and role on one assignment; treats First Tracks and Night Ski as shifts; validates hard rules; respects manual locks; and returns structured conflicts instead of weakening policy.

## Run

```bash
python -m pip install -e '.[dev]'
patrol-demo --pretty
pytest
```

The demo creates deterministic synthetic data and prints a complete valid week as JSON. The normalized models and solver are independent of spreadsheet layouts and future UI code.
