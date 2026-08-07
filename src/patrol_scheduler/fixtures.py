from __future__ import annotations

from datetime import date, time

from .models import (
    Employee,
    EmployeeSeasonStats,
    EmploymentType,
    RookieStatus,
    ShiftKind,
    ShiftType,
    SolverConfig,
    SpecialtyShiftRequirement,
    StationRequirement,
)


def synthetic_week() -> tuple[
    date,
    list[Employee],
    dict[str, tuple[int, ...]],
    SolverConfig,
    dict[str, EmployeeSeasonStats],
]:
    """Deterministic, configuration-driven demonstration data (not production identities)."""
    week_start = date(2030, 1, 6)
    employees: list[Employee] = []
    patterns: dict[str, tuple[int, ...]] = {}
    contiguous = tuple(
        tuple((start + offset) % 7 for offset in range(4)) for start in range(7)
    )
    for index in range(42):
        employee_id = f"FT-{index + 1:03d}"
        supervisor = index < 14
        rookie = index >= 40
        employees.append(
            Employee(
                id=employee_id,
                first_name="Synthetic",
                last_name=f"Patroller {index + 1:03d}",
                employment_type=EmploymentType.FULL_TIME,
                supervisor=supervisor,
                prior_winter_hours=float(2000 - index * 20),
                seniority_rank=index + 1,
                rookie_status=RookieStatus.ROOKIE if rookie else RookieStatus.GRADUATED,
                qualifications={"ROUTE_LEADER", "SKIER"}
                if index % 3 == 0
                else ({"SKIER"} if index % 2 == 0 else set()),
                night_ski_eligible=not rookie,
                first_tracks_eligible=not rookie,
            )
        )
        patterns[employee_id] = contiguous[index % len(contiguous)]
    for index, workdays in enumerate(((0, 1, 2, 3, 4), (2, 3, 4, 5, 6))):
        employee_id = f"MGR-{index + 1:03d}"
        employees.append(
            Employee(
                employee_id,
                "Synthetic",
                f"Manager {index + 1:03d}",
                EmploymentType.MANAGER,
                supervisor=True,
                manager=True,
                night_ski_eligible=False,
                first_tracks_eligible=False,
            )
        )
        patterns[employee_id] = workdays

    shifts = (
        ShiftType("STANDARD", ShiftKind.STANDARD, time(7, 15), time(17, 15), 10),
        ShiftType("FIRST_TRACKS", ShiftKind.FIRST_TRACKS, time(6), time(16), 10),
        ShiftType("NIGHT_SKI", ShiftKind.NIGHT_SKI, time(12), time(22), 10),
    )
    config = SolverConfig(
        normal_shifts_per_week=4,
        manager_shifts_per_week=5,
        max_weekly_hours=40,
        max_same_station_per_week=2,
        manager_station_id="DERCUM",
        rookie_station_id="DERCUM",
        station_requirements=(
            StationRequirement("DERCUM", 4),
            StationRequirement("NORTH_PEAK", 3, 1),
            StationRequirement("OUTBACK", 3, 1),
            StationRequirement("BERGMAN", 3, 1),
        ),
        specialty_shift_requirements=(
            SpecialtyShiftRequirement("FIRST_TRACKS", 2, 1),
            SpecialtyShiftRequirement("NIGHT_SKI", 2, 1),
        ),
        shift_types=shifts,
        fairness_weight=1,
    )
    history = {
        e.id: EmployeeSeasonStats(
            e.id,
            dercum_days=(i * 2) % 9,
            north_peak_days=i % 5,
            outback_days=(i + 2) % 5,
            bergman_days=(i + 4) % 5,
        )
        for i, e in enumerate(employees)
    }
    return week_start, employees, patterns, config, history
