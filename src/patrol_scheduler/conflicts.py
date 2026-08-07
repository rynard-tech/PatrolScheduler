from __future__ import annotations

from .models import Conflict, Shift, Station, WeeklyInput


RESOLUTIONS = (
    "add part-time coverage",
    "move an employee work pattern",
    "activate another qualified employee",
    "approve a documented override",
    "modify the staffing requirement",
    "modify the hard budget",
)


def analyze_conflicts(data: WeeklyInput) -> list[Conflict]:
    """Report provable shortages without claiming to explain every CP conflict."""
    employees = {employee.id: employee for employee in data.employees}
    conflicts: list[Conflict] = []
    for day, requirements in sorted(data.requirements_by_date.items()):
        working = [
            employees[employee_id]
            for employee_id, days in data.workdays.items()
            if day in days
            and employee_id in employees
            and day not in data.unavailable.get(employee_id, set())
            and day not in data.approved_pto.get(employee_id, set())
        ]
        minimum = sum(
            requirement.minimum for requirement in requirements.station_requirements
        )
        if len(working) < minimum:
            conflicts.append(
                Conflict(
                    "DAILY_STAFF_SHORTAGE",
                    day,
                    f"Daily station minimums require {minimum} people but only {len(working)} are available.",
                    minimum,
                    len(working),
                    RESOLUTIONS,
                )
            )
        if (
            requirements.max_paid_hours is not None
            and minimum * 10 > requirements.max_paid_hours
        ):
            conflicts.append(
                Conflict(
                    "BUDGET_CONFLICT",
                    day,
                    "Minimum operational staffing exceeds the hard paid-hours budget.",
                    minimum * 10,
                    requirements.max_paid_hours,
                    RESOLUTIONS,
                )
            )
        for station_requirement in requirements.station_requirements:
            for role in station_requirement.roles:
                eligible = sum(
                    role.qualification in employee.qualifications
                    and _station_allowed(employee, station_requirement.station)
                    for employee in working
                )
                if eligible < role.count:
                    conflicts.append(
                        Conflict(
                            "QUALIFICATION_SHORTAGE",
                            day,
                            f"{station_requirement.station.value} requires {role.count} {role.role}; {eligible} qualified scheduled employees are available.",
                            role.count,
                            eligible,
                            RESOLUTIONS,
                        )
                    )
        for shift_requirement in requirements.shift_requirements:
            eligible = [
                employee
                for employee in working
                if _shift_allowed(employee, shift_requirement.shift)
            ]
            supervisors = sum(employee.supervisor for employee in eligible)
            if len(eligible) < shift_requirement.count:
                conflicts.append(
                    Conflict(
                        "SHIFT_ELIGIBILITY_SHORTAGE",
                        day,
                        f"{shift_requirement.shift.value} requires {shift_requirement.count} eligible employees; {len(eligible)} are available.",
                        shift_requirement.count,
                        len(eligible),
                        RESOLUTIONS,
                    )
                )
            if supervisors < shift_requirement.supervisor_count:
                conflicts.append(
                    Conflict(
                        "SHIFT_SUPERVISOR_SHORTAGE",
                        day,
                        f"{shift_requirement.shift.value} requires {shift_requirement.supervisor_count} supervisor; {supervisors} eligible supervisors are available.",
                        shift_requirement.supervisor_count,
                        supervisors,
                        RESOLUTIONS,
                    )
                )
    if not conflicts:
        conflicts.append(
            Conflict(
                "COMBINED_CONSTRAINT_CONFLICT",
                None,
                "No valid assignment satisfies all hard rules and locks; no single shortage was provable.",
                resolutions=RESOLUTIONS,
            )
        )
    return conflicts


def _station_allowed(employee, station: Station) -> bool:
    if employee.manager or employee.rookie_status.value == "ROOKIE":
        return station == Station.DERCUM
    if employee.required_station:
        return station == employee.required_station
    return station not in employee.prohibited_stations and (
        not employee.allowed_stations or station in employee.allowed_stations
    )


def _shift_allowed(employee, shift: Shift) -> bool:
    if shift == Shift.NIGHT_SKI:
        return employee.night_ski_eligible
    if shift == Shift.FIRST_TRACKS:
        return employee.first_tracks_eligible
    return True
