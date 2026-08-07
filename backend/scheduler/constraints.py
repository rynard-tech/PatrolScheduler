"""Hard-constraint predicates, deliberately separate from optimization policy."""

from collections import Counter
from typing import Iterable, Mapping

from .models import Employee, Pattern, QualificationRequirement, SolverConfig


def feasible_patterns(employee: Employee, patterns: Iterable[Pattern], config: SolverConfig) -> list[Pattern]:
    """Return explicit patterns satisfying availability and the configured normal week."""
    if not employee.normal_ft:
        return []
    return [
        pattern for pattern in patterns
        if len(pattern.weekdays) == config.ft_shifts_per_week
        and pattern.weekdays <= employee.available_weekdays
        and len(pattern.weekdays) * config.paid_hours_per_shift <= config.max_ft_hours_per_week
    ]


def staffing_for(assignments: Mapping[str, Pattern]) -> Counter[int]:
    staffing: Counter[int] = Counter()
    for pattern in assignments.values():
        staffing.update(pattern.weekdays)
    return staffing


def hard_constraints_hold(
    employees: Mapping[str, Employee],
    assignments: Mapping[str, Pattern],
    config: SolverConfig,
) -> bool:
    """Validate hours, budget, availability, and configured qualification minima."""
    if config.max_budgeted_hours is not None:
        if len(assignments) * config.ft_shifts_per_week * config.paid_hours_per_shift > config.max_budgeted_hours:
            return False
    for employee_id, pattern in assignments.items():
        employee = employees[employee_id]
        if not employee.normal_ft or len(pattern.weekdays) != config.ft_shifts_per_week:
            return False
        if not pattern.weekdays <= employee.available_weekdays:
            return False
        if len(pattern.weekdays) * config.paid_hours_per_shift > config.max_ft_hours_per_week:
            return False
    for requirement in config.qualification_requirements:
        if not _qualification_met(requirement, employees, assignments):
            return False
    return True


def _qualification_met(
    requirement: QualificationRequirement,
    employees: Mapping[str, Employee],
    assignments: Mapping[str, Pattern],
) -> bool:
    for day, minimum in requirement.minimum_by_weekday.items():
        actual = sum(
            day in pattern.weekdays and requirement.qualification in employees[employee_id].qualifications
            for employee_id, pattern in assignments.items()
        )
        if actual < minimum:
            return False
    return True
