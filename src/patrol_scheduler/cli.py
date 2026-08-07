from __future__ import annotations

import argparse
import json

from .fixtures import synthetic_week
from .solver import DeploymentSolver
from .validation import validate


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a synthetic valid patrol deployment week"
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    data = synthetic_week()
    result = DeploymentSolver().solve(data)
    result.warnings.extend(
        issue.message for issue in validate(data, result.assignments)
    )
    print(json.dumps(result.to_dict(), indent=2 if args.pretty else None))
    raise SystemExit(
        0 if result.status in ("OPTIMAL", "FEASIBLE") and not result.warnings else 1
    )


if __name__ == "__main__":
    main()
