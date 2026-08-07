"""Normalized scheduling input and output models for the synthetic MVP."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

WEEKDAYS = ("SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT")

class EmploymentType(str, Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    MANAGER = "MANAGER"

@dataclass(frozen=True)
class WorkPattern:
    id: str
    weekdays: tuple[str, ...]
    split: bool = False

@dataclass(frozen=True)
class RankedPattern:
    pattern_id: str
    rank: int

@dataclass
class Employee:
    id: str
    display_name: str
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    supervisor: bool = False
    manager: bool = False
    prior_winter_hours: int = 0
    qualifications: set[str] = field(default_factory=set)
    ranked_patterns: list[RankedPattern] = field(default_factory=list)
    wave_preferences: list[str] = field(default_factory=list)
    special_role_eligibility: set[str] = field(default_factory=set)
    explicit_paid_weekdays: tuple[str, ...] = ()

    @property
    def normal_full_time(self) -> bool:
        return self.employment_type == EmploymentType.FULL_TIME and not self.manager and not self.explicit_paid_weekdays

@dataclass(frozen=True)
class StaffingRequirement:
    weekday: str
    minimum_staff: int
    qualification: str | None = None
    qualified_count: int = 0

@dataclass(frozen=True)
class OperatingPeriod:
    name: str
    weekdays: tuple[str, ...] = WEEKDAYS
    requirements: tuple[StaffingRequirement, ...] = ()
    max_budgeted_hours: int | None = None

@dataclass(frozen=True)
class StaffingWave:
    id: str
    active_employee_count: int
    target_people_per_day: float

@dataclass
class ScheduleInput:
    employees: list[Employee]
    patterns: list[WorkPattern]
    operating_period: OperatingPeriod
    waves: list[StaffingWave] = field(default_factory=list)
    selected_wave_id: str | None = None
    shift_hours: int = 10

@dataclass(frozen=True)
class Assignment:
    employee_id: str
    weekday: str
    worked: bool
    paid_hours: int
    status: str = "WORKED"

@dataclass
class SolveResult:
    status: str
    assignments: list[Assignment] = field(default_factory=list)
    awarded_patterns: dict[str, str] = field(default_factory=dict)
    active_employees: list[str] = field(default_factory=list)
    shortages: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
