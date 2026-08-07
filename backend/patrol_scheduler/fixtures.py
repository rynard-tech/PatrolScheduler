"""Deterministic, configurable synthetic data; no real employee identities are used."""
from __future__ import annotations
from dataclasses import dataclass
from .models import *

CONTIGUOUS = {
    "SUN_WED": ("SUN", "MON", "TUE", "WED"), "MON_THU": ("MON", "TUE", "WED", "THU"),
    "TUE_FRI": ("TUE", "WED", "THU", "FRI"), "WED_SAT": ("WED", "THU", "FRI", "SAT"),
    "THU_SUN": ("THU", "FRI", "SAT", "SUN"), "FRI_MON": ("FRI", "SAT", "SUN", "MON"),
    "SAT_TUE": ("SAT", "SUN", "MON", "TUE"),
}

@dataclass(frozen=True)
class FixtureConfig:
    employee_count: int = 14
    supervisor_count: int = 2
    manager_count: int = 2
    split_pattern_count: int = 2
    split_pattern_weekdays: tuple[str, ...] = ("SUN", "TUE", "THU", "SAT")
    contiguous_patterns: dict[str, tuple[str, ...]] | None = None
    target_people_per_day: int = 8
    max_budgeted_hours: int | None = None
    qualification_counts: dict[str, int] | None = None
    staffing_requirements: tuple[StaffingRequirement, ...] | None = None
    operating_period_name: str = "Synthetic full week"
    operating_weekdays: tuple[str, ...] = WEEKDAYS
    special_role_eligible_count: int = 2
    special_roles: tuple[str, ...] = ("WEATHER",)
    wave_active_counts: tuple[int, ...] = (14,)
    wave_target_people_per_day: tuple[float, ...] = (8.0,)


def synthetic_week(config: FixtureConfig = FixtureConfig()) -> ScheduleInput:
    if config.supervisor_count + config.manager_count > config.employee_count:
        raise ValueError("supervisor_count + manager_count exceeds employee_count")
    contiguous = config.contiguous_patterns or CONTIGUOUS
    patterns = [WorkPattern(k, v) for k, v in contiguous.items()]
    patterns += [WorkPattern(f"SPLIT_{i+1}", config.split_pattern_weekdays, True)
                 for i in range(config.split_pattern_count)]
    employees: list[Employee] = []
    quals = config.qualification_counts or {"avalanche": max(2, config.employee_count // 4)}
    for i in range(config.employee_count):
        manager = i < config.manager_count
        supervisor = config.manager_count <= i < config.manager_count + config.supervisor_count
        ranked_ids = list(contiguous)
        rotation = i % len(ranked_ids)
        ranked_ids = ranked_ids[rotation:] + ranked_ids[:rotation]
        if i >= config.employee_count - config.split_pattern_count:
            ranked_ids = [f"SPLIT_{i - (config.employee_count-config.split_pattern_count)+1}"]
        qualifications = {q for q, count in quals.items() if i < count}
        employees.append(Employee(
            id=f"E{i+1:03}", display_name=f"Synthetic Employee {i+1:03}",
            employment_type=EmploymentType.MANAGER if manager else EmploymentType.FULL_TIME,
            manager=manager, supervisor=supervisor, prior_winter_hours=(config.employee_count-i)*100,
            qualifications=qualifications,
            ranked_patterns=[RankedPattern(pid, rank+1) for rank, pid in enumerate(ranked_ids)],
            wave_preferences=[f"WAVE_{j+1}" for j in range(len(config.wave_active_counts))],
            special_role_eligibility=set(config.special_roles) if i < config.special_role_eligible_count else set(),
        ))
    requirements = config.staffing_requirements or tuple(
        StaffingRequirement(day, config.target_people_per_day) for day in config.operating_weekdays)
    period = OperatingPeriod(config.operating_period_name, weekdays=config.operating_weekdays,
                             requirements=requirements, max_budgeted_hours=config.max_budgeted_hours)
    waves = [StaffingWave(f"WAVE_{i+1}", count, config.wave_target_people_per_day[i])
             for i, count in enumerate(config.wave_active_counts)]
    return ScheduleInput(employees, patterns, period, waves, waves[-1].id)
