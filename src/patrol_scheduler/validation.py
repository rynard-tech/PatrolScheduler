from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .models import (
    DailyAssignment,
    RookieStatus,
    RuleStrength,
    Shift,
    Station,
    WeeklyInput,
)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


def validate(
    data: WeeklyInput, assignments: list[DailyAssignment]
) -> list[ValidationIssue]:
    """Independently check important hard constraints after solve or manual edit."""
    issues = []
    employees = {employee.id: employee for employee in data.employees}
    by_key = {
        (assignment.employee_id, assignment.day): assignment
        for assignment in assignments
    }
    for employee_id, workdays in data.workdays.items():
        expected = (
            workdays
            - data.unavailable.get(employee_id, set())
            - data.approved_pto.get(employee_id, set())
        )
        actual = {day for eid, day in by_key if eid == employee_id}
        if expected & set(data.requirements_by_date) != actual:
            issues.append(
                ValidationIssue(
                    "ASSIGNMENT_COVERAGE",
                    f"{employee_id} does not have exactly one assignment on every scheduled available day.",
                )
            )
    for assignment in assignments:
        employee = employees[assignment.employee_id]
        if (
            employee.manager or employee.rookie_status == RookieStatus.ROOKIE
        ) and assignment.station != Station.DERCUM:
            issues.append(
                ValidationIssue(
                    "STATION_RESTRICTION", f"{employee.id} must remain at DERCUM."
                )
            )
    if data.config.station_repeat_rule == RuleStrength.HARD:
        counts = Counter((a.employee_id, a.station) for a in assignments)
        for (employee_id, station), count in counts.items():
            employee = employees[employee_id]
            exempt = (
                employee.manager
                or employee.rookie_status == RookieStatus.ROOKIE
                or employee.required_station
                or employee_id in data.repeat_overrides
            )
            if not exempt and count > data.config.station_max_repeats:
                issues.append(
                    ValidationIssue(
                        "STATION_REPEAT",
                        f"{employee_id} has {count} {station.value} assignments; maximum is {data.config.station_max_repeats}.",
                    )
                )
    for day, requirements in data.requirements_by_date.items():
        daily = [assignment for assignment in assignments if assignment.day == day]
        for requirement in requirements.station_requirements:
            count = sum(a.station == requirement.station for a in daily)
            if count < requirement.minimum:
                issues.append(
                    ValidationIssue(
                        "STATION_MINIMUM",
                        f"{day} {requirement.station.value} has {count}; requires {requirement.minimum}.",
                    )
                )
            for role in requirement.roles:
                count = sum(
                    a.station == requirement.station and a.role == role.role
                    for a in daily
                )
                if count < role.count:
                    issues.append(
                        ValidationIssue(
                            "ROLE_MINIMUM",
                            f"{day} {requirement.station.value} has {count} {role.role}; requires {role.count}.",
                        )
                    )
        for requirement in requirements.shift_requirements:
            shifted = [a for a in daily if a.shift == requirement.shift]
            supervisors = sum(employees[a.employee_id].supervisor for a in shifted)
            if (
                len(shifted) != requirement.count
                or supervisors != requirement.supervisor_count
            ):
                issues.append(
                    ValidationIssue(
                        "SHIFT_REQUIREMENT",
                        f"{day} {requirement.shift.value} staffing or supervision is invalid.",
                    )
                )
        ft_supervisors = {
            a.employee_id
            for a in daily
            if a.shift == Shift.FIRST_TRACKS and employees[a.employee_id].supervisor
        }
        ns_supervisors = {
            a.employee_id
            for a in daily
            if a.shift == Shift.NIGHT_SKI and employees[a.employee_id].supervisor
        }
        if ft_supervisors & ns_supervisors:
            issues.append(
                ValidationIssue(
                    "SPECIALTY_SUPERVISOR_CONFLICT",
                    f"{day} uses the same First Tracks and Night Ski supervisor.",
                )
            )
    return issues
