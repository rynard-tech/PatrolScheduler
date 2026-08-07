"""Date-effective operational requirements.

These are persistence-friendly value objects: IDs, counts, dates, and priorities are
data, rather than constants hidden in the scheduling implementation.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Mapping


class DutyStation(StrEnum):
    DERCUM = "DERCUM"
    NORTH_PEAK = "NORTH_PEAK"
    OUTBACK = "OUTBACK"
    BERGMAN = "BERGMAN"


class RequirementStrength(StrEnum):
    HARD = "HARD"
    SOFT = "SOFT"


class SpecialRole(StrEnum):
    WEATHER = "WEATHER"
    SNOW_SAFETY = "SNOW_SAFETY"
    BLASTER = "BLASTER"
    FORECASTER = "FORECASTER"
    MGMT_SUPERVISOR = "MGMT_SUPERVISOR"
    SNOWMOBILE_DRIVER = "SNOWMOBILE_DRIVER"
    TRUCK_DRIVER = "TRUCK_DRIVER"


@dataclass(frozen=True)
class StationRequirement:
    station: str
    minimum_staff: int
    target_staff: int
    qualification_counts: Mapping[str, int] = field(default_factory=dict)
    qualification_strengths: Mapping[str, RequirementStrength] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.minimum_staff < 0 or self.target_staff < self.minimum_staff:
            raise ValueError("station target must be at least its non-negative minimum")
        if any(count < 0 for count in self.qualification_counts.values()):
            raise ValueError("qualification counts cannot be negative")


@dataclass(frozen=True)
class SpecialRoleRequirement:
    """A generic role requirement; ``role`` may contain future custom role IDs."""

    id: str
    role: str
    required_count: int
    strength: RequirementStrength
    start_date: date | None = None
    end_date: date | None = None
    weekdays: frozenset[int] = frozenset(range(7))
    required_station: str | None = None
    required_shift_type: str | None = None
    eligibility_qualification: str | None = None
    preferred_employee_ids: tuple[str, ...] = ()
    backup_employee_ids: tuple[str, ...] = ()
    priority_weight: int = 1
    notes: str = ""

    def __post_init__(self) -> None:
        if self.required_count < 0:
            raise ValueError("required_count cannot be negative")
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValueError("end_date precedes start_date")
        if not self.weekdays.issubset(range(7)):
            raise ValueError("weekdays use Python's 0=Monday through 6=Sunday")
        if self.priority_weight < 0:
            raise ValueError("priority_weight cannot be negative")

    def applies_on(self, day: date) -> bool:
        return (
            day.weekday() in self.weekdays
            and (self.start_date is None or day >= self.start_date)
            and (self.end_date is None or day <= self.end_date)
        )


@dataclass(frozen=True)
class RequirementSet:
    name: str
    station_requirements: tuple[StationRequirement, ...]
    special_role_requirements: tuple[SpecialRoleRequirement, ...] = ()
    remainder_station: str = DutyStation.DERCUM


def full_operations_requirement_set() -> RequirementSet:
    """Return editable seed configuration for normal full operations."""
    southside = (
        StationRequirement(
            DutyStation.BERGMAN, 7, 7,
            {"SUPERVISOR": 1, "AVALANCHE_ROUTE_LEADER": 2,
             "PROSPECTIVE_ROUTE_LEADER": 2, "SKIER": 4},
            {"SKIER": RequirementStrength.SOFT},
        ),
        StationRequirement(
            DutyStation.OUTBACK, 7, 7,
            {"SUPERVISOR": 1, "AVALANCHE_ROUTE_LEADER": 2,
             "PROSPECTIVE_ROUTE_LEADER": 2, "SKIER": 4},
            {"SKIER": RequirementStrength.SOFT},
        ),
        StationRequirement(
            DutyStation.NORTH_PEAK, 7, 7,
            {"TEAM_LEAD": 1, "SUPERVISOR": 1},
        ),
        # No staffing floor or cap: Dercum receives everyone not required elsewhere.
        StationRequirement(DutyStation.DERCUM, 0, 0),
    )
    roles = (
        SpecialRoleRequirement("weather", SpecialRole.WEATHER, 1, RequirementStrength.HARD,
                               required_shift_type="WEATHER", eligibility_qualification="WEATHER"),
        SpecialRoleRequirement("snow_safety", SpecialRole.SNOW_SAFETY, 1, RequirementStrength.HARD,
                               required_station=DutyStation.BERGMAN,
                               eligibility_qualification="SNOW_SAFETY"),
        SpecialRoleRequirement("forecaster", SpecialRole.FORECASTER, 1, RequirementStrength.HARD,
                               required_station=DutyStation.DERCUM,
                               required_shift_type="FORECASTER", eligibility_qualification="FORECASTER"),
        SpecialRoleRequirement("mgmt_supervisor", SpecialRole.MGMT_SUPERVISOR, 1,
                               RequirementStrength.HARD, required_station=DutyStation.DERCUM,
                               eligibility_qualification="MGMT_SUPERVISOR"),
        SpecialRoleRequirement("snowmobile_driver", SpecialRole.SNOWMOBILE_DRIVER, 1,
                               RequirementStrength.HARD, required_station=DutyStation.DERCUM,
                               eligibility_qualification="SNOWMOBILE_DRIVER"),
        SpecialRoleRequirement("truck_driver", SpecialRole.TRUCK_DRIVER, 1,
                               RequirementStrength.HARD, required_station=DutyStation.DERCUM,
                               eligibility_qualification="TRUCK_DRIVER"),
    )
    return RequirementSet("FULL_OPERATIONS", southside, roles)
