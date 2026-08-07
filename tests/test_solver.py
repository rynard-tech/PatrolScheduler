from collections import Counter

from patrol_scheduler.fixtures import synthetic_week
from patrol_scheduler.models import AssignmentLock, RookieStatus, Shift, Station
from patrol_scheduler.solver import DeploymentSolver
from patrol_scheduler.validation import validate


def solve_fixture():
    data = synthetic_week()
    result = DeploymentSolver().solve(data)
    assert result.status in {"OPTIMAL", "FEASIBLE"}, [
        c.message for c in result.conflicts
    ]
    return data, result


def test_complete_week_passes_independent_validation():
    data, result = solve_fixture()
    assert len(result.assignments) == sum(len(days) for days in data.workdays.values())
    assert validate(data, result.assignments) == []


def test_manager_rookie_and_hard_rotation_rules():
    data, result = solve_fixture()
    employees = {employee.id: employee for employee in data.employees}
    counts = Counter(
        (assignment.employee_id, assignment.station)
        for assignment in result.assignments
    )
    for assignment in result.assignments:
        employee = employees[assignment.employee_id]
        if employee.manager or employee.rookie_status == RookieStatus.ROOKIE:
            assert assignment.station == Station.DERCUM
    for (employee_id, _station), count in counts.items():
        employee = employees[employee_id]
        if not employee.manager and employee.rookie_status == RookieStatus.GRADUATED:
            assert count <= 2


def test_specialty_shift_counts_and_distinct_supervisors():
    data, result = solve_fixture()
    employees = {employee.id: employee for employee in data.employees}
    for day, requirements in data.requirements_by_date.items():
        daily = [
            assignment for assignment in result.assignments if assignment.day == day
        ]
        for requirement in requirements.shift_requirements:
            selected = [
                assignment
                for assignment in daily
                if assignment.shift == requirement.shift
            ]
            assert len(selected) == requirement.count
            assert sum(employees[a.employee_id].supervisor for a in selected) == 1
        ft_supervisor = next(
            a.employee_id
            for a in daily
            if a.shift == Shift.FIRST_TRACKS and employees[a.employee_id].supervisor
        )
        ns_supervisor = next(
            a.employee_id
            for a in daily
            if a.shift == Shift.NIGHT_SKI and employees[a.employee_id].supervisor
        )
        assert ft_supervisor != ns_supervisor


def test_assignment_lock_is_preserved_on_resolve():
    data, initial = solve_fixture()
    candidate = next(
        a
        for a in initial.assignments
        if a.station != Station.DERCUM and a.role == "PATROLLER"
    )
    data.locks.append(
        AssignmentLock(
            candidate.employee_id, candidate.day, candidate.station, candidate.shift
        )
    )
    result = DeploymentSolver().solve(data)
    locked = next(
        a
        for a in result.assignments
        if a.employee_id == candidate.employee_id and a.day == candidate.day
    )
    assert locked.station == candidate.station
    assert locked.shift == candidate.shift
    assert locked.locked


def test_pto_is_never_assigned():
    data = synthetic_week()
    employee_id = "E020"
    day = next(iter(data.workdays[employee_id]))
    data.approved_pto[employee_id] = {day}
    result = DeploymentSolver().solve(data)
    assert result.status in {"OPTIMAL", "FEASIBLE"}
    assert (employee_id, day) not in {
        (a.employee_id, a.day) for a in result.assignments
    }


def test_shortage_returns_structured_infeasibility():
    data = synthetic_week()
    day = data.week_start
    data.workdays = {
        employee_id: days - {day} for employee_id, days in data.workdays.items()
    }
    result = DeploymentSolver().solve(data)
    assert result.status == "INFEASIBLE"
    assert any(
        conflict.code == "DAILY_STAFF_SHORTAGE" and conflict.day == day
        for conflict in result.conflicts
    )
    assert result.conflicts[0].resolutions
