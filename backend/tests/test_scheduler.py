from patrol_scheduler.fixtures import FixtureConfig, synthetic_week
from patrol_scheduler.models import *
from patrol_scheduler.solver import solve_week


def worked(result, employee_id):
    return [a for a in result.assignments if a.employee_id == employee_id and a.worked]


def test_normal_full_time_get_exactly_four_tens_and_never_overtime():
    data = synthetic_week(FixtureConfig(employee_count=14, manager_count=0, target_people_per_day=8,
                                        wave_active_counts=(14,), wave_target_people_per_day=(8,)))
    result = solve_week(data)
    assert result.status in {"VALID", "VALID_WITH_SHORTAGES"}
    assert result.validation["valid"]
    for employee in data.employees:
        shifts = worked(result, employee.id)
        assert len(shifts) == 4
        assert {a.paid_hours for a in shifts} == {10}
        assert sum(a.paid_hours for a in shifts) == 40


def test_split_pattern_preserves_explicit_weekdays():
    data = synthetic_week(FixtureConfig(employee_count=8, manager_count=0, supervisor_count=0,
                                        split_pattern_count=1, target_people_per_day=4,
                                        wave_active_counts=(8,), wave_target_people_per_day=(4,)))
    result = solve_week(data)
    split_employee = data.employees[-1]
    assert result.awarded_patterns[split_employee.id] == "SPLIT_1"
    assert {a.weekday for a in worked(result, split_employee.id)} == {"SUN", "TUE", "THU", "SAT"}


def test_managers_and_explicit_paid_statuses_are_exempt_from_normal_ft_math():
    data = synthetic_week(FixtureConfig(employee_count=5, manager_count=1, supervisor_count=0,
                                        split_pattern_count=0, target_people_per_day=2,
                                        wave_active_counts=(5,), wave_target_people_per_day=(2,)))
    explicit = data.employees[-1]
    explicit.explicit_paid_weekdays = ("MON", "TUE")
    result = solve_week(data)
    assert len(worked(result, data.employees[0].id)) == 5
    assert len(worked(result, explicit.id)) == 2
    assert explicit.id not in result.awarded_patterns
    assert result.validation["valid"]


def test_seniority_breaks_otherwise_equivalent_pattern_award():
    patterns = [WorkPattern("A", ("SUN", "MON", "TUE", "WED")),
                WorkPattern("B", ("THU", "FRI", "SAT", "SUN"))]
    employees = [Employee("SENIOR", "Senior", prior_winter_hours=1000,
                          ranked_patterns=[RankedPattern("A", 1), RankedPattern("B", 2)]),
                 Employee("JUNIOR", "Junior", prior_winter_hours=100,
                          ranked_patterns=[RankedPattern("A", 1), RankedPattern("B", 2)])]
    period = OperatingPeriod("week", requirements=tuple(StaffingRequirement(d, 1) for d in WEEKDAYS))
    result = solve_week(ScheduleInput(employees, patterns, period, [StaffingWave("W", 2, 1)], "W"))
    assert result.awarded_patterns == {"SENIOR": "A", "JUNIOR": "B"}


def test_wave_and_pattern_selection_balance_all_seven_days():
    data = synthetic_week(FixtureConfig(employee_count=14, manager_count=0, supervisor_count=0,
                                        target_people_per_day=8, wave_active_counts=(14,),
                                        wave_target_people_per_day=(8,)))
    result = solve_week(data)
    coverage = [sum(a.worked for a in result.assignments if a.weekday == day) for day in WEEKDAYS]
    assert max(coverage) - min(coverage) <= 1
    assert len(result.active_employees) == 14


def test_hard_budget_contradiction_is_infeasible():
    data = synthetic_week(FixtureConfig(employee_count=7, manager_count=0, supervisor_count=0,
                                        split_pattern_count=0, target_people_per_day=4,
                                        max_budgeted_hours=270, wave_active_counts=(7,),
                                        wave_target_people_per_day=(4,)))
    result = solve_week(data)
    assert result.status == "INFEASIBLE"
    assert result.conflicts


def test_hard_qualification_contradiction_is_infeasible():
    data = synthetic_week(FixtureConfig(employee_count=7, manager_count=0, supervisor_count=0,
                                        qualification_counts={"avalanche": 0}, wave_active_counts=(7,),
                                        wave_target_people_per_day=(4,)))
    data.operating_period = OperatingPeriod("week", requirements=(
        StaffingRequirement("MON", 4, qualification="avalanche", qualified_count=1),))
    result = solve_week(data)
    assert result.status == "INFEASIBLE"
    assert "qualification avalanche" in result.conflicts[0]


def test_shortages_are_reported_instead_of_adding_overtime():
    data = synthetic_week(FixtureConfig(employee_count=7, manager_count=0, supervisor_count=0,
                                        split_pattern_count=0, target_people_per_day=5,
                                        wave_active_counts=(7,), wave_target_people_per_day=(5,)))
    result = solve_week(data)
    assert result.status == "VALID_WITH_SHORTAGES"
    assert result.shortages
    assert all(sum(a.paid_hours for a in worked(result, e.id)) <= 40 for e in data.employees)
