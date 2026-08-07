from backend.scheduler import Employee, Pattern, QualificationRequirement, SolverConfig, solve_wave, solve_work_patterns
from backend.scheduler.models import SolveStatus
from backend.scheduler.wave_solver import planning_estimate


PATTERNS = [
    Pattern("SUN_WED", frozenset({0, 1, 2, 3})),
    Pattern("THU_SUN", frozenset({0, 4, 5, 6})),
    Pattern("SPLIT", frozenset({0, 2, 4, 6})),
]


def test_normal_ft_get_exactly_four_ten_hour_shifts_globally():
    employees = [
        Employee("senior", "Senior", pattern_preferences=("SUN_WED", "THU_SUN"), seniority_rank=1),
        Employee("junior", "Junior", pattern_preferences=("SUN_WED", "THU_SUN"), seniority_rank=2),
    ]
    result = solve_work_patterns(employees, PATTERNS, SolverConfig(staffing_targets={d: 1 for d in range(7)}))
    assert result.status == SolveStatus.OPTIMAL
    assert all(award.paid_hours == 40 for award in result.awards)
    assert next(a for a in result.awards if a.employee_id == "senior").awarded_ranking == 1
    assert next(a for a in result.awards if a.employee_id == "junior").explanation


def test_manager_and_paid_status_exception_are_excluded():
    employees = [Employee("ft", "FT", pattern_preferences=("SPLIT",)),
                 Employee("manager", "Manager", manager=True),
                 Employee("leave", "Leave", paid_status_exception=True)]
    result = solve_work_patterns(employees, PATTERNS, SolverConfig())
    assert [award.employee_id for award in result.awards] == ["ft"]


def test_joint_wave_selection_honors_budget_and_qualification():
    employees = [
        Employee("qualified", "Qualified", qualifications=frozenset({"supervisor"}), pattern_preferences=("SPLIT",)),
        Employee("unqualified", "Unqualified", pattern_preferences=("SPLIT",), seniority_rank=1),
    ]
    config = SolverConfig(
        staffing_targets={day: int(day in {0, 2, 4, 6}) for day in range(7)}, max_budgeted_hours=40,
        qualification_requirements=(QualificationRequirement("supervisor", {0: 1, 2: 1, 4: 1, 6: 1}),),
    )
    result = solve_wave(employees, PATTERNS, config)
    assert result.status == SolveStatus.OPTIMAL
    assert next(a for a in result.awards if a.employee_id == "qualified").active
    assert not next(a for a in result.awards if a.employee_id == "unqualified").active
    assert result.planning_estimate == planning_estimate(4 / 7, 4)


def test_infeasible_instead_of_fifth_shift_or_budget_violation():
    config = SolverConfig(max_budgeted_hours=39,
                          qualification_requirements=(QualificationRequirement("supervisor", {0: 1}),))
    result = solve_work_patterns([Employee("ft", "FT", qualifications=frozenset({"supervisor"}))], PATTERNS, config)
    assert result.status == SolveStatus.INFEASIBLE
    assert result.conflicts
