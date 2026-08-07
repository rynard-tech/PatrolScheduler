"""Global exact work-pattern solver for an already-active normal FT roster."""

from itertools import product
from time import monotonic
from typing import Iterable

from .constraints import feasible_patterns, hard_constraints_hold, staffing_for
from .models import Employee, EmployeeAward, Pattern, SolveStatus, SolverConfig, SolverResult, WEEKDAYS
from .objectives import lexicographic_key, preference_value, staffing_deviation


def solve_work_patterns(employees: Iterable[Employee], patterns: Iterable[Pattern], config: SolverConfig) -> SolverResult:
    roster = {employee.id: employee for employee in employees if employee.normal_ft}
    pattern_list = tuple(patterns)
    choices = {employee_id: feasible_patterns(employee, pattern_list, config) for employee_id, employee in roster.items()}
    missing = [employee_id for employee_id, options in choices.items() if not options]
    if missing:
        return _infeasible(config, [f"No available {config.ft_shifts_per_week}-day pattern for {employee_id}" for employee_id in missing])

    best = _search(roster, choices, config)
    if best is None:
        return _infeasible(config, ["No assignment satisfies configured availability, qualification, and budget requirements"])
    return _result(roster, best, config)


def _search(roster, choices, config):
    employee_ids = tuple(sorted(roster))
    best = None
    best_key = None
    deadline = monotonic() + config.time_limit_seconds
    for selected in product(*(choices[employee_id] for employee_id in employee_ids)):
        if monotonic() > deadline:
            break
        assignment = dict(zip(employee_ids, selected))
        if hard_constraints_hold(roster, assignment, config):
            key = lexicographic_key(roster, assignment, config)
            if best_key is None or key < best_key:
                best, best_key = assignment, key
    return best


def _result(roster, assignment, config, planning_estimate=None):
    staffing = staffing_for(assignment)
    awards = []
    for employee_id in sorted(roster):
        employee, pattern = roster[employee_id], assignment[employee_id]
        rank = employee.pattern_preferences.index(pattern.id) + 1 if pattern.id in employee.pattern_preferences else None
        explanation = None
        if rank != 1 and employee.pattern_preferences:
            explanation = "Selected as part of the globally optimized staffing solution; no single binding cause was proven."
        awards.append(EmployeeAward(employee_id, True, pattern.id, rank, employee.seniority_rank,
                                    len(pattern.weekdays) * config.paid_hours_per_shift, explanation))
    return SolverResult(
        SolveStatus.OPTIMAL, {WEEKDAYS[d]: staffing[d] for d in range(7)}, awards,
        {"staffing_deviation": staffing_deviation(assignment, config),
         "seniority_weighted_preference_value": preference_value(roster, assignment),
         "objective_order": "staffing_deviation, seniority_weighted_preferences"}, planning_estimate,
    )


def _infeasible(config, conflicts):
    return SolverResult(SolveStatus.INFEASIBLE, {day: 0 for day in WEEKDAYS}, (), {}, conflicts=conflicts)
