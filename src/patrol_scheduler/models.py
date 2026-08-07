from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, time
from enum import StrEnum
from typing import Any


class EmploymentType(StrEnum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    MANAGER = "MANAGER"


class RookieStatus(StrEnum):
    ROOKIE = "ROOKIE"
    GRADUATED = "GRADUATED"


class Station(StrEnum):
    DERCUM = "DERCUM"
    NORTH_PEAK = "NORTH_PEAK"
    OUTBACK = "OUTBACK"
    BERGMAN = "BERGMAN"


class Shift(StrEnum):
    STANDARD = "STANDARD"
    FIRST_TRACKS = "FIRST_TRACKS"
    NIGHT_SKI = "NIGHT_SKI"


class RuleStrength(StrEnum):
    HARD = "HARD"
    SOFT = "SOFT"


@dataclass(frozen=True)
class Season:
    id: str
    name: str
    start_date: date
    end_date: date


@dataclass
class Employee:
    id: str
    first_name: str
    last_name: str
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    active: bool = True
    employee_number: str | None = None
    supervisor: bool = False
    rookie_status: RookieStatus = RookieStatus.GRADUATED
    qualifications: set[str] = field(default_factory=set)
    required_station: Station | None = None
    allowed_stations: set[Station] = field(default_factory=set)
    prohibited_stations: set[Station] = field(default_factory=set)
    night_ski_eligible: bool = False
    first_tracks_eligible: bool = True
    winter_hours: int = 0
    family_supervisor_id: str | None = None

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def manager(self) -> bool:
        return self.employment_type == EmploymentType.MANAGER


@dataclass(frozen=True)
class RoleRequirement:
    role: str
    count: int
    qualification: str


@dataclass(frozen=True)
class StationRequirement:
    station: Station
    minimum: int
    target: int
    roles: tuple[RoleRequirement, ...] = ()


@dataclass(frozen=True)
class ShiftRequirement:
    shift: Shift
    count: int
    supervisor_count: int = 1


@dataclass(frozen=True)
class RequirementSet:
    station_requirements: tuple[StationRequirement, ...]
    shift_requirements: tuple[ShiftRequirement, ...] = ()
    max_paid_hours: int | None = None


@dataclass(frozen=True)
class ShiftDefinition:
    shift: Shift
    start: time
    end: time
    paid_hours: int = 10


DEFAULT_SHIFTS = {
    Shift.STANDARD: ShiftDefinition(Shift.STANDARD, time(7, 15), time(17, 15)),
    Shift.FIRST_TRACKS: ShiftDefinition(Shift.FIRST_TRACKS, time(6), time(16)),
    Shift.NIGHT_SKI: ShiftDefinition(Shift.NIGHT_SKI, time(12), time(22)),
}


@dataclass(frozen=True)
class AssignmentLock:
    employee_id: str
    day: date
    station: Station | None = None
    shift: Shift | None = None
    role: str | None = None


@dataclass(frozen=True)
class SolverConfig:
    station_repeat_rule: RuleStrength = RuleStrength.HARD
    station_max_repeats: int = 2
    time_limit_seconds: float = 30.0
    random_seed: int = 17


@dataclass
class WeeklyInput:
    season: Season
    week_start: date
    employees: list[Employee]
    workdays: dict[str, set[date]]
    requirements_by_date: dict[date, RequirementSet]
    unavailable: dict[str, set[date]] = field(default_factory=dict)
    approved_pto: dict[str, set[date]] = field(default_factory=dict)
    station_history: dict[str, dict[Station, int]] = field(default_factory=dict)
    family_exposure: dict[tuple[str, str], int] = field(default_factory=dict)
    manager_supervisor_exposure: dict[tuple[str, str], int] = field(
        default_factory=dict
    )
    locks: list[AssignmentLock] = field(default_factory=list)
    repeat_overrides: set[str] = field(default_factory=set)
    config: SolverConfig = field(default_factory=SolverConfig)


@dataclass(frozen=True)
class DailyAssignment:
    employee_id: str
    employee_name: str
    day: date
    shift: Shift
    station: Station
    role: str
    start_time: time
    end_time: time
    paid_hours: int
    locked: bool = False
    generated_by_solver: bool = True

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for key in ("day", "start_time", "end_time"):
            result[key] = result[key].isoformat()
        return result


@dataclass(frozen=True)
class Conflict:
    code: str
    day: date | None
    message: str
    required: int | None = None
    available: int | None = None
    resolutions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["day"] = self.day.isoformat() if self.day else None
        return result


@dataclass
class SolveResult:
    status: str
    assignments: list[DailyAssignment] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    solve_time_seconds: float = 0
    objective_values: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "solve_time_seconds": round(self.solve_time_seconds, 4),
            "objective_values": self.objective_values,
            "warnings": self.warnings,
            "conflicts": [item.to_dict() for item in self.conflicts],
            "assignments": [item.to_dict() for item in self.assignments],
        }
