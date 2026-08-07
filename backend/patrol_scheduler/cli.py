"""Solve and print one complete deterministic synthetic week."""
import argparse, json
from .fixtures import FixtureConfig, synthetic_week
from .models import WEEKDAYS
from .solver import solve_week

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--employees", type=int, default=14)
    parser.add_argument("--target", type=int, default=8)
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()
    data = synthetic_week(FixtureConfig(employee_count=args.employees, target_people_per_day=args.target,
                                        wave_active_counts=(args.employees,), wave_target_people_per_day=(args.target,)))
    result = solve_week(data)
    print(json.dumps(result.to_dict(), indent=2))
    if not args.json_only:
        worked = {(a.employee_id, a.weekday) for a in result.assignments if a.worked}
        print("\nSYNTHETIC WEEK (X = worked ten-hour shift)")
        print(f"Status: {result.status}; validation: {'PASS' if result.validation.get('valid') else 'FAIL'}")
        print(f"{'EMPLOYEE':<10} " + " ".join(f"{d:>3}" for d in WEEKDAYS))
        for e in data.employees:
            print(f"{e.id:<10} " + " ".join("  X" if (e.id,d) in worked else "  ." for d in WEEKDAYS))
        print("Shortages: " + (json.dumps(result.shortages) if result.shortages else "none"))
    return 0 if result.status != "INFEASIBLE" else 2

if __name__ == "__main__": raise SystemExit(main())
