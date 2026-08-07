"""Transport models shared by solver modules.

Weekdays are always integer indexes from Sunday (0) through Saturday (6).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Mapping, Sequence


WEEKDAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")


class SolveStatus(str, Enum):
    OPTIMAL = "OPTIMAL"
    INFEASIBLE = "INFEASIBLE"


@dataclass(frozen=True)
class Pattern:
    id: str
    weekdays: FrozenSet[int]

    def __post_init__(self) -> None:
        if not self.weekdays <= frozenset(range(7)):
            raise ValueError("pattern weekdays must be in the range 0..6")


@dataclass(frozen=True)
class Employee:
    id: str
    display_name: str
    employment_type: str = "FULL_TIME"
    supervisor: bool = False
    manager: bool = False
    paid_status_exception: bool = False
    available_weekdays: FrozenSet[int] = frozenset(range(7))
    qualifications: FrozenSet[str] = frozenset()
    pattern_preferences: Sequence[str] = ()
    wave_preference_rank: int | None = None
    seniority_rank: int = 1
    required_active: bool = False

    @property
    def normal_ft(self) -> bool:
        return (
            self.employment_type == "FULL_TIME"
            and not self.manager
            and not self.paid_status_exception
        )


@dataclass(frozen=True)
class QualificationRequirement:
    qualification: str
    minimum_by_weekday: Mapping[int, int]


@dataclass(frozen=True)
class SolverConfig:
    ft_shifts_per_week: int = 4
    paid_hours_per_shift: int = 10
    max_ft_hours_per_week: int = 40
    staffing_targets: Mapping[int, int] = field(default_factory=lambda: {day: 0 for day in range(7)})
    qualification_requirements: Sequence[QualificationRequirement] = ()
    max_budgeted_hours: int | None = None
    time_limit_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.ft_shifts_per_week * self.paid_hours_per_shift > self.max_ft_hours_per_week:
            raise ValueError("configured normal work week exceeds the FT weekly-hours limit")
        if self.ft_shifts_per_week <= 0 or self.paid_hours_per_shift <= 0:
            raise ValueError("shift count and paid hours must be positive")


@dataclass(frozen=True)
class EmployeeAward:
    employee_id: str
    active: bool
    pattern_id: str | None
    awarded_ranking: int | None
    seniority_rank: int
    paid_hours: int
    explanation: str | None = None


@dataclass(frozen=True)
class SolverResult:
    status: SolveStatus
    projected_staffing: Mapping[str, int]
    awards: Sequence[EmployeeAward]
    objective_data: Mapping[str, int | float | str]
    planning_estimate: float | None = None
    conflicts: Sequence[str] = ()
