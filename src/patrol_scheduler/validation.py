from __future__ import annotations

from collections import Counter

from .models import Employee, RookieStatus, ScheduleResult, SolverConfig


def validate_schedule(
    result: ScheduleResult, employees: list[Employee], config: SolverConfig
) -> list[dict[str, str]]:
    """Independent post-solve checks: a result with violations must not be called valid."""
    violations: list[dict[str, str]] = []
    if result.status not in {"OPTIMAL", "FEASIBLE"}:
        return [
            {
                "code": "NO_VALID_SCHEDULE",
                "message": "Solver did not return a complete valid schedule",
            }
        ]
    by_employee = Counter(a.employee_id for a in result.assignments)
    hours = Counter()
    repeats: dict[str, Counter] = {}
    by_day_station = Counter((a.day, a.duty_station_id) for a in result.assignments)
    by_day_shift = Counter((a.day, a.shift_type_id) for a in result.assignments)
    shift_hours = {s.id: s.paid_hours for s in config.shift_types}
    for assignment in result.assignments:
        hours[assignment.employee_id] += shift_hours[assignment.shift_type_id]
        repeats.setdefault(assignment.employee_id, Counter())[
            assignment.duty_station_id
        ] += 1
    for employee in employees:
        expected = (
            config.manager_shifts_per_week
            if employee.manager
            else config.normal_shifts_per_week
        )
        if by_employee[employee.id] != expected:
            violations.append(
                {
                    "code": "SHIFT_COUNT",
                    "message": f"{employee.id}: {by_employee[employee.id]} != {expected}",
                }
            )
        if not employee.manager and hours[employee.id] > config.max_weekly_hours:
            violations.append({"code": "OVERTIME", "message": employee.id})
        if employee.manager and any(
            a.duty_station_id != config.manager_station_id
            for a in result.assignments
            if a.employee_id == employee.id
        ):
            violations.append({"code": "MANAGER_STATION", "message": employee.id})
        if employee.rookie_status == RookieStatus.ROOKIE and any(
            a.duty_station_id != config.rookie_station_id
            for a in result.assignments
            if a.employee_id == employee.id
        ):
            violations.append({"code": "ROOKIE_STATION", "message": employee.id})
        if (
            employee.rookie_status == RookieStatus.GRADUATED
            and not employee.manager
            and max(repeats.get(employee.id, Counter()).values(), default=0)
            > config.max_same_station_per_week
        ):
            violations.append({"code": "STATION_DIVERSITY", "message": employee.id})
    days = {a.day for a in result.assignments}
    for day in days:
        for requirement in config.station_requirements:
            if by_day_station[day, requirement.station_id] < requirement.minimum_staff:
                violations.append(
                    {
                        "code": "STATION_SHORTAGE",
                        "message": f"{day} {requirement.station_id}",
                    }
                )
        for requirement in config.specialty_shift_requirements:
            if (
                day.weekday() in requirement.active_weekdays
                and by_day_shift[day, requirement.shift_type_id] != requirement.count
            ):
                violations.append(
                    {
                        "code": "SHIFT_SHORTAGE",
                        "message": f"{day} {requirement.shift_type_id}",
                    }
                )
    return violations
