from __future__ import annotations

import argparse
import json
from pathlib import Path

from .fixtures import synthetic_week
from .solver import WeeklyDeploymentSolver
from .validation import validate_schedule


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PatrolScheduler command line interface"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("demo", help="solve a complete synthetic week")
    demo.add_argument("--json", type=Path, help="write structured schedule JSON")
    args = parser.parse_args()
    week, employees, patterns, config, history = synthetic_week()
    result = WeeklyDeploymentSolver().solve(week, employees, patterns, config, history)
    violations = validate_schedule(result, employees, config)
    payload = result.to_dict()
    payload["validation"] = {"valid": not violations, "violations": violations}
    if args.json:
        args.json.write_text(json.dumps(payload, indent=2) + "\n")
    print(
        f"Status: {result.status} | assignments: {len(result.assignments)} | solve: {result.solve_time_seconds:.3f}s"
    )
    if result.conflicts:
        for conflict in result.conflicts:
            print(f"CONFLICT {conflict['category']}: {conflict['message']}")
        return 2
    print("DATE       STATION       SHIFT          EMPLOYEE")
    for assignment in sorted(
        result.assignments,
        key=lambda a: (a.day, a.duty_station_id, a.shift_type_id, a.employee_id),
    ):
        print(
            f"{assignment.day} {assignment.duty_station_id:<13} {assignment.shift_type_id:<14} {assignment.employee_id}"
        )
    return 0 if not violations else 3


if __name__ == "__main__":
    raise SystemExit(main())
