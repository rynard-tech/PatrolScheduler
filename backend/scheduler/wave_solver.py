"""Joint active-roster and work-pattern optimization for a staffing wave."""

from itertools import combinations, product
from time import monotonic
from typing import Iterable

from .constraints import feasible_patterns, hard_constraints_hold
from .models import Employee, EmployeeAward, Pattern, SolverConfig
from .objectives import lexicographic_key
from .work_pattern_solver import _infeasible, _result


def planning_estimate(target_people_per_day: float, configured_ft_shifts_per_week: int) -> float:
    """Display-only headcount estimate; it is not a coverage validation."""
    if configured_ft_shifts_per_week <= 0:
        raise ValueError("configured_ft_shifts_per_week must be positive")
    return target_people_per_day * 7 / configured_ft_shifts_per_week


def solve_wave(employees: Iterable[Employee], patterns: Iterable[Pattern], config: SolverConfig):
    roster = {employee.id: employee for employee in employees if employee.normal_ft}
    options = {employee_id: feasible_patterns(employee, patterns, config) for employee_id, employee in roster.items()}
    selectable = [employee_id for employee_id in sorted(roster) if options[employee_id]]
    required = {employee_id for employee_id, employee in roster.items() if employee.required_active}
    max_active = len(selectable)
    if config.max_budgeted_hours is not None:
        hours_per_employee = config.ft_shifts_per_week * config.paid_hours_per_shift
        max_active = min(max_active, config.max_budgeted_hours // hours_per_employee)
    estimate = planning_estimate(
        sum(config.staffing_targets.get(day, 0) for day in range(7)) / 7,
        config.ft_shifts_per_week,
    )
    best = best_roster = None
    best_key = None
    deadline = monotonic() + config.time_limit_seconds
    for count in range(len(required), max_active + 1):
        for active_tuple in combinations(selectable, count):
            active = set(active_tuple)
            if not required <= active:
                continue
            active_roster = {employee_id: roster[employee_id] for employee_id in active_tuple}
            for selected in product(*(options[employee_id] for employee_id in active_tuple)):
                if monotonic() > deadline:
                    break
                assignment = dict(zip(active_tuple, selected))
                if hard_constraints_hold(active_roster, assignment, config):
                    key = lexicographic_key(active_roster, assignment, config)
                    if best_key is None or key < best_key:
                        best, best_roster, best_key = assignment, active_roster, key
    if best is None:
        return _infeasible(config, ["No joint active-roster and pattern assignment satisfies hard budget and qualification requirements"])
    result = _result(best_roster, best, config, estimate)
    inactive = [
        # Explicitly report employees considered but not activated.
        EmployeeAward(
            employee_id, False, None, None, roster[employee_id].seniority_rank, 0,
            "Not activated by the globally optimized wave solution.")
        for employee_id in sorted(set(roster) - set(best_roster))
    ]
    return result.__class__(result.status, result.projected_staffing, tuple(result.awards) + tuple(inactive),
                            result.objective_data, result.planning_estimate, result.conflicts)
