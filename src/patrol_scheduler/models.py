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


class RuleStrength(StrEnum):
    HARD = "HARD"
    SOFT = "SOFT"
    INFORMATIONAL = "INFORMATIONAL"


class ShiftKind(StrEnum):
    STANDARD = "STANDARD"
    FIRST_TRACKS = "FIRST_TRACKS"
    NIGHT_SKI = "NIGHT_SKI"
    CUSTOM = "CUSTOM"


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
    employment_type: EmploymentType
    employee_number: str | None = None
    active: bool = True
    supervisor: bool = False
    manager: bool = False
    prior_winter_hours: float = 0
    seniority_rank: int | None = None
    rookie_status: RookieStatus = RookieStatus.GRADUATED
    qualifications: set[str] = field(default_factory=set)
    family_id: str | None = None
    unavailable_weekdays: set[int] = field(default_factory=set)
    free_text_notes: str = ""
    night_ski_eligible: bool = False
    first_tracks_eligible: bool = False

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


@dataclass(frozen=True)
class WorkPatternPreference:
    employee_id: str
    weekdays: tuple[int, ...]
    rank: int


@dataclass(frozen=True)
class StaffingWave:
    id: str
    name: str
    effective_date: date
    target_people_per_day: float
    end_date: date | None = None
    max_budgeted_hours: float | None = None


@dataclass(frozen=True)
class Family:
    id: str
    name: str
    supervisor_employee_id: str


@dataclass(frozen=True)
class EmployeeSeasonStats:
    employee_id: str
    dercum_days: int = 0
    north_peak_days: int = 0
    outback_days: int = 0
    bergman_days: int = 0
    first_tracks_days: int = 0
    night_ski_days: int = 0
    recent_station_sequence: tuple[str, ...] = ()

    @property
    def southside_total(self) -> int:
        return self.north_peak_days + self.outback_days + self.bergman_days


@dataclass(frozen=True)
class PartTimeAvailability:
    employee_id: str
    day: date
    available: bool
    preferred: bool = False
    notes: str = ""


@dataclass(frozen=True)
class ShiftType:
    id: str
    kind: ShiftKind
    start_time: time
    end_time: time
    paid_hours: float


@dataclass(frozen=True)
class StationRequirement:
    station_id: str
    minimum_staff: int
    supervisor_count: int = 0
    qualification_minimums: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class SpecialtyShiftRequirement:
    shift_type_id: str
    count: int
    supervisor_count: int = 0
    active_weekdays: frozenset[int] = frozenset(range(7))


@dataclass(frozen=True)
class SolverConfig:
    normal_shifts_per_week: int
    manager_shifts_per_week: int
    max_weekly_hours: float
    max_same_station_per_week: int
    manager_station_id: str
    rookie_station_id: str
    station_requirements: tuple[StationRequirement, ...]
    specialty_shift_requirements: tuple[SpecialtyShiftRequirement, ...]
    shift_types: tuple[ShiftType, ...]
    hard_budget_hours: float | None = None
    fairness_weight: int = 1
    family_exposure_weight: int = 1
    manager_exposure_weight: int = 1
    solver_time_limit_seconds: float = 20


@dataclass(frozen=True)
class LockedAssignment:
    employee_id: str
    day: date
    station_id: str | None = None
    shift_type_id: str | None = None


@dataclass(frozen=True)
class DailyAssignment:
    employee_id: str
    day: date
    working: bool
    shift_type_id: str
    duty_station_id: str
    paid_hours: float
    locked: bool = False
    generated_by_solver: bool = True


@dataclass
class ScheduleResult:
    status: str
    assignments: list[DailyAssignment] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    objective_value: float | None = None
    solve_time_seconds: float = 0

    def to_dict(self) -> dict[str, Any]:
        def convert(value: Any) -> Any:
            if isinstance(value, (date, time)):
                return value.isoformat()
            if isinstance(value, set | frozenset | tuple):
                return [convert(v) for v in value]
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            if isinstance(value, list):
                return [convert(v) for v in value]
            return value

        return convert(asdict(self))
