from copy import deepcopy

from backend.scheduler.conflict_analysis import analyze_conflicts
from backend.scheduler.validation import ScheduleValidator


def _week(employee_id="ft", station="DERCUM"):
    return [
        {"employee_id": employee_id, "date": f"2026-12-0{day}", "working": True,
         "paid_hours": 10, "shift_type": "STANDARD", "duty_station": station}
        for day in range(1, 5)
    ]


def test_validates_rules_independently_and_does_not_mutate_schedule():
    assignments = _week()
    original = deepcopy(assignments)
    employees = [{"id": "ft", "employment_type": "FULL_TIME", "qualifications": ["skier"]}]
    requirements = [
        {"date": "2026-12-01", "station": "DERCUM", "minimum": 1},
        {"date": "2026-12-01", "qualification": "skier", "required_count": 1},
        {"date": "2026-12-01", "role": "WEATHER", "required_count": 1},
    ]
    report = ScheduleValidator().validate(
        assignments, employees, requirements,
        budgets=[{"date": "2026-12-01", "max_hours": 5, "behavior": "HARD_LIMIT"}],
        availability=[{"employee_id": "ft", "date": "2026-12-02", "available": False}],
        time_off=[{"employee_id": "ft", "date": "2026-12-03", "status": "APPROVED"}],
        locks=[{"employee_id": "ft", "date": "2026-12-04", "fields": ["duty_station"], "duty_station": "OUTBACK"}],
    )
    assert {x.category for x in report.issues} == {
        "special_role", "budget_limit", "availability", "approved_time_off", "locked_decision"
    }
    assert assignments == original


def test_shift_and_hour_limits_are_separate_findings():
    assignments = _week() + [{"employee_id": "ft", "date": "2026-12-05", "paid_hours": 10}]
    report = ScheduleValidator().validate(assignments, [{"id": "ft", "employment_type": "FULL_TIME"}])
    assert {x.category for x in report.issues} == {"shift_count", "overtime"}


def test_shortage_excludes_people_who_would_need_fifth_shift_or_overtime():
    employees = [{"id": "s1", "qualifications": ["supervisor"]}, {"id": "s2", "qualifications": ["supervisor"]}]
    report = analyze_conflicts(
        employees,
        [{"date": "2026-12-05", "qualification": "supervisor", "shift_type": "NIGHT_SKI", "required_count": 2}],
        existing_weekly_load={"s1": (4, 40), "s2": (3, 30)},
    )
    shortage = report.shortages[0]
    assert (shortage.required_count, shortage.available_count_without_overtime, shortage.unfilled_count) == (2, 1, 1)
    assert report.conflicts[0].category == "insufficient_supervisors"
    assert report.conflicts[0].possible_resolutions


def test_hard_budget_and_approved_absence_conflicts_are_structured():
    report = analyze_conflicts(
        [{"id": "p1"}],
        [{"date": "2026-12-06", "name": "daily staffing", "required_count": 2, "paid_hours": 10}],
        time_off=[{"employee_id": "p1", "date": "2026-12-06", "status": "APPROVED"}],
        budgets=[{"date": "2026-12-06", "max_hours": 10, "behavior": "HARD_LIMIT"}],
    )
    assert {x.category for x in report.conflicts} == {
        "approved_absence_conflicts", "hard_budget_below_minimum_staffing"
    }
    assert all(x.possible_resolutions for x in report.conflicts)
