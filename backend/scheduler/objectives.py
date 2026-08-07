"""Lexicographic objective components; hard requirements never appear here."""

from typing import Mapping

from .models import Employee, Pattern, SolverConfig


def staffing_deviation(assignments: Mapping[str, Pattern], config: SolverConfig) -> int:
    counts = {day: 0 for day in range(7)}
    for pattern in assignments.values():
        for day in pattern.weekdays:
            counts[day] += 1
    return sum(abs(counts[day] - config.staffing_targets.get(day, 0)) for day in range(7))


def preference_value(employees: Mapping[str, Employee], assignments: Mapping[str, Pattern]) -> int:
    """Seniority magnifies rank value without crossing the staffing objective stage."""
    roster_size = max(len(employees), 1)
    value = 0
    for employee_id, pattern in assignments.items():
        employee = employees[employee_id]
        try:
            preference_rank = employee.pattern_preferences.index(pattern.id) + 1
        except ValueError:
            preference_rank = len(employee.pattern_preferences) + 1
        seniority_weight = roster_size - min(max(employee.seniority_rank, 1), roster_size) + 1
        rank_value = max(len(employee.pattern_preferences) + 2 - preference_rank, 0)
        wave_value = 0 if employee.wave_preference_rank is None else max(5 - employee.wave_preference_rank, 0)
        value += seniority_weight * (rank_value + wave_value)
    return value


def lexicographic_key(
    employees: Mapping[str, Employee], assignments: Mapping[str, Pattern], config: SolverConfig
) -> tuple[int, int, tuple[tuple[str, str], ...]]:
    # Deterministic final tie break makes repeated solves stable.
    return (
        staffing_deviation(assignments, config),
        -preference_value(employees, assignments),
        tuple(sorted((employee_id, pattern.id) for employee_id, pattern in assignments.items())),
    )
