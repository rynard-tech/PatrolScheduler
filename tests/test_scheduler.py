from datetime import timedelta

from patrol_scheduler.fixtures import synthetic_week
from patrol_scheduler.models import LockedAssignment
from patrol_scheduler.solver import WeeklyDeploymentSolver
from patrol_scheduler.validation import validate_schedule


def test_synthetic_week_satisfies_hard_constraints():
    week, employees, patterns, config, history = synthetic_week()
    result = WeeklyDeploymentSolver().solve(week, employees, patterns, config, history)
    assert result.status in {"OPTIMAL", "FEASIBLE"}, result.conflicts
    assert validate_schedule(result, employees, config) == []


def test_overtime_is_reported_instead_of_scheduled():
    week, employees, patterns, config, history = synthetic_week()
    patterns[employees[0].id] = (0, 1, 2, 3, 4)
    result = WeeklyDeploymentSolver().solve(week, employees, patterns, config, history)
    assert result.status == "INFEASIBLE"
    assert {c["category"] for c in result.conflicts} >= {
        "INVALID_WORK_PATTERN",
        "OVERTIME",
    }
    assert result.assignments == []


def test_invalid_lock_is_reported():
    week, employees, patterns, config, history = synthetic_week()
    employee = employees[0]
    non_working = next(day for day in range(7) if day not in patterns[employee.id])
    lock = LockedAssignment(employee.id, week + timedelta(days=non_working), "DERCUM")
    result = WeeklyDeploymentSolver().solve(
        week, employees, patterns, config, history, (lock,)
    )
    assert result.status == "INFEASIBLE"
    assert result.conflicts[0]["category"] == "INVALID_LOCK"
