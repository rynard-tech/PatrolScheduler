"""Pre-solve analysis for contradictory operating inputs and shortages."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Iterable

from .explanations import possible_resolutions
from .validation import ShortageRecord, _day, _get


@dataclass(frozen=True)
class InputConflict:
    category: str
    date: date
    requirement: str
    required_count: float
    available_count: float
    details: dict[str, Any] = field(default_factory=dict)
    possible_resolutions: tuple[str, ...] = ()

    def to_dict(self):
        result = asdict(self)
        result["date"] = self.date.isoformat()
        result["possible_resolutions"] = list(self.possible_resolutions)
        return result


@dataclass
class ConflictReport:
    conflicts: list[InputConflict] = field(default_factory=list)
    shortages: list[ShortageRecord] = field(default_factory=list)

    @property
    def feasible(self): return not self.conflicts and not self.shortages
    def to_dict(self): return {"feasible": self.feasible, "conflicts": [x.to_dict() for x in self.conflicts], "shortages": [x.to_dict() for x in self.shortages]}


def analyze_conflicts(employees: Iterable[Any], requirements: Iterable[Any], *,
                      availability: Iterable[Any] = (), time_off: Iterable[Any] = (),
                      budgets: Iterable[Any] = (), existing_weekly_load: dict[str, tuple[int, float]] | None = None) -> ConflictReport:
    """Compare date-effective hard inputs without modifying any schedule.

    ``existing_weekly_load`` maps employee id to already committed (shifts,
    hours); employees at four shifts or forty hours are excluded from the
    no-overtime availability count.
    """
    report = ConflictReport()
    employees = list(employees)
    loads = existing_weekly_load or {}
    unavailable = {(str(_get(x, "employee_id")), _day(x)) for x in availability if not _get(x, "available", True)}
    approved = {(str(_get(x, "employee_id")), _day(x)) for x in time_off if _get(x, "status") in {"APPROVED", "OVERRIDE_APPROVED"}}
    budget_by_day = {_day(x): x for x in budgets if _get(x, "behavior", "HARD_LIMIT") == "HARD_LIMIT"}
    for req in requirements:
        day, required = _day(req), int(_get(req, "required_count", _get(req, "minimum", 0)))
        qualification = _get(req, "qualification")
        label = qualification or _get(req, "role") or _get(req, "shift_type") or _get(req, "station") or _get(req, "name", "coverage")
        eligible = [e for e in employees if _get(e, "active", True) and (not qualification or qualification in set(_get(e, "qualifications", ())))]
        no_ot = [e for e in eligible if (str(_get(e, "id")), day) not in unavailable | approved and loads.get(str(_get(e, "id")), (0, 0))[0] < 4 and loads.get(str(_get(e, "id")), (0, 0))[1] + float(_get(req, "paid_hours", 10)) <= 40]
        if len(no_ot) < required:
            report.shortages.append(ShortageRecord(day, day.weekday(), str(label), required, len(no_ot), required-len(no_ot), _get(req, "shift_type")))
            if qualification == "supervisor" or _get(req, "supervisor_required", False): category = "insufficient_supervisors"
            elif qualification: category = "insufficient_qualification_holders"
            elif any((str(_get(e, "id")), day) in approved for e in eligible): category = "approved_absence_conflicts"
            else: category = "insufficient_qualification_holders"
            report.conflicts.append(InputConflict(category, day, str(label), required, len(no_ot), possible_resolutions=tuple(possible_resolutions(category))))
        budget = budget_by_day.get(day)
        if budget:
            hours = float(_get(req, "paid_hours", 10)) * required
            limit = float(_get(budget, "max_hours"))
            if hours > limit:
                category = "hard_budget_below_minimum_staffing"
                report.conflicts.append(InputConflict(category, day, str(label), hours, limit, {"units": "paid_hours"}, tuple(possible_resolutions(category))))
    return report
