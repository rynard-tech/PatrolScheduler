from __future__ import annotations

from datetime import date, timedelta

from .models import (
    Employee,
    EmploymentType,
    RequirementSet,
    RoleRequirement,
    RookieStatus,
    Season,
    Shift,
    ShiftRequirement,
    Station,
    StationRequirement,
    WeeklyInput,
)


def synthetic_week(
    week_start: date = date(2026, 1, 4), employee_count: int = 40
) -> WeeklyInput:
    """Create configurable, deterministic fixture data for a complete week."""
    if employee_count < 32:
        raise ValueError("The full-operations fixture needs at least 32 employees")
    employees = []
    for index in range(employee_count):
        manager = index < 2
        supervisor = index < 12
        qualifications = {"SKIER"} if index % 3 else {"SNOWBOARDER"}
        if index < 18:
            qualifications.add("ROUTE_LEADER")
        if index < 26:
            qualifications.add("PROSPECTIVE_LEADER")
        if index < 14:
            qualifications.add("TEAM_LEAD")
        if supervisor:
            qualifications.add("SUPERVISOR")
        employees.append(
            Employee(
                id=f"E{index:03}",
                first_name=f"Patroller{index:03}",
                last_name="Synthetic",
                employment_type=EmploymentType.MANAGER
                if manager
                else (
                    EmploymentType.PART_TIME
                    if index >= int(employee_count * 0.75)
                    else EmploymentType.FULL_TIME
                ),
                supervisor=supervisor,
                rookie_status=RookieStatus.ROOKIE
                if index in (employee_count - 1, employee_count - 2)
                else RookieStatus.GRADUATED,
                qualifications=qualifications,
                night_ski_eligible=index < employee_count - 2,
                winter_hours=(employee_count - index) * 100,
                family_supervisor_id="E002" if index in (20, 21, 22) else None,
            )
        )
    days = [week_start + timedelta(days=offset) for offset in range(7)]
    workdays = {}
    for index, employee in enumerate(employees):
        shifts = 5 if employee.manager else 4
        workdays[employee.id] = {days[(index + offset) % 7] for offset in range(shifts)}
    # Managers overlap enough days, and 40-person scale supplies 22-24 per day.
    station_requirements = (
        StationRequirement(
            Station.BERGMAN,
            5,
            5,
            (
                RoleRequirement("SUPERVISOR", 1, "SUPERVISOR"),
                RoleRequirement("ROUTE_LEADER", 1, "ROUTE_LEADER"),
                RoleRequirement("PROSPECTIVE_LEADER", 1, "PROSPECTIVE_LEADER"),
            ),
        ),
        StationRequirement(
            Station.OUTBACK,
            5,
            5,
            (
                RoleRequirement("SUPERVISOR", 1, "SUPERVISOR"),
                RoleRequirement("ROUTE_LEADER", 1, "ROUTE_LEADER"),
                RoleRequirement("PROSPECTIVE_LEADER", 1, "PROSPECTIVE_LEADER"),
            ),
        ),
        StationRequirement(
            Station.NORTH_PEAK,
            4,
            4,
            (
                RoleRequirement("SUPERVISOR", 1, "SUPERVISOR"),
                RoleRequirement("TEAM_LEAD", 1, "TEAM_LEAD"),
            ),
        ),
        StationRequirement(Station.DERCUM, 4, 6),
    )
    requirements = {
        day: RequirementSet(
            station_requirements,
            (
                ShiftRequirement(Shift.FIRST_TRACKS, 3),
                ShiftRequirement(Shift.NIGHT_SKI, 3),
            ),
        )
        for day in days
    }
    history = {
        employee.id: {
            station: (index + station_index) % 7
            for station_index, station in enumerate(Station)
        }
        for index, employee in enumerate(employees)
    }
    return WeeklyInput(
        Season("S26", "2025-2026", date(2025, 10, 1), date(2026, 5, 31)),
        week_start,
        employees,
        workdays,
        requirements,
        station_history=history,
    )
