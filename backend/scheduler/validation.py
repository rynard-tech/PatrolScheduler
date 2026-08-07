"""Objective-independent validation of generated or manually edited schedules.

The validator deliberately consumes dictionaries as well as model objects.  This
keeps it usable by the CLI, API schemas, and the eventual persistence models
without duplicating scheduling policy in any of those layers.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping


def _get(value: Any, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(value, Mapping) else getattr(value, name, default)


def _day(value: Any) -> date:
    value = _get(value, "date", value)
    return value if isinstance(value, date) else date.fromisoformat(str(value))


@dataclass(frozen=True)
class ValidationIssue:
    category: str
    message: str
    date: date | None = None
    employee_id: str | None = None
    requirement: str | None = None
    expected: float | None = None
    actual: float | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["date"] = self.date.isoformat() if self.date else None
        return result


@dataclass(frozen=True)
class ShortageRecord:
    date: date | None
    weekday: int | None
    requirement: str
    required_count: int
    available_count_without_overtime: int
    unfilled_count: int
    shift_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["date"] = self.date.isoformat() if self.date else None
        return result


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)
    shortages: list[ShortageRecord] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.issues and not self.shortages

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "issues": [x.to_dict() for x in self.issues],
                "shortages": [x.to_dict() for x in self.shortages]}


class ScheduleValidator:
    """Validate hard rules without evaluating or changing objective scores."""

    def __init__(self, *, normal_shifts: int = 4, max_hours: float = 40,
                 manager_shifts: int = 5):
        self.normal_shifts = normal_shifts
        self.max_hours = max_hours
        self.manager_shifts = manager_shifts

    def validate(self, assignments: Iterable[Any], employees: Iterable[Any],
                 requirements: Iterable[Any] = (), *, budgets: Iterable[Any] = (),
                 availability: Iterable[Any] = (), time_off: Iterable[Any] = (),
                 locks: Iterable[Any] = ()) -> ValidationReport:
        report = ValidationReport()
        assignments = list(assignments)
        employees_by_id = {str(_get(e, "id")): e for e in employees}
        worked = [a for a in assignments if _get(a, "working", True)]
        by_employee: dict[str, list[Any]] = defaultdict(list)
        by_date: dict[date, list[Any]] = defaultdict(list)
        for assignment in worked:
            employee_id = str(_get(assignment, "employee_id"))
            by_employee[employee_id].append(assignment)
            by_date[_day(assignment)].append(assignment)

        self._validate_counts_hours(report, employees_by_id, by_employee)
        self._validate_availability(report, worked, availability, time_off)
        self._validate_locks(report, assignments, locks)
        self._validate_requirements(report, by_date, employees_by_id, requirements)
        self._validate_budgets(report, by_date, budgets)
        return report

    def _validate_counts_hours(self, report, employees, by_employee):
        for employee_id, employee in employees.items():
            if not _get(employee, "active", True) or _get(employee, "employment_type") == "PART_TIME":
                continue
            shifts = len(by_employee[employee_id])
            hours = sum(float(_get(a, "paid_hours", 0)) for a in by_employee[employee_id])
            expected = self.manager_shifts if _get(employee, "manager_flag", False) or _get(employee, "employment_type") == "MANAGER" else self.normal_shifts
            if shifts != expected:
                report.issues.append(ValidationIssue("shift_count", f"Employee has {shifts} worked shifts; {expected} required", employee_id=employee_id, expected=expected, actual=shifts))
            if expected == self.normal_shifts and hours != self.max_hours:
                category = "paid_hours" if hours < self.max_hours else "overtime"
                report.issues.append(ValidationIssue(category, f"Employee has {hours:g} paid hours; {self.max_hours:g} required/maximum", employee_id=employee_id, expected=self.max_hours, actual=hours))

    def _validate_availability(self, report, worked, availability, time_off):
        unavailable = {(str(_get(x, "employee_id")), _day(x)) for x in availability if not _get(x, "available", True)}
        approved = {(str(_get(x, "employee_id")), _day(x)) for x in time_off if _get(x, "status") in {"APPROVED", "OVERRIDE_APPROVED"}}
        for assignment in worked:
            key = (str(_get(assignment, "employee_id")), _day(assignment))
            if key in unavailable:
                report.issues.append(ValidationIssue("availability", "Assignment violates hard unavailability", key[1], key[0]))
            if key in approved:
                report.issues.append(ValidationIssue("approved_time_off", "Assignment conflicts with approved time off", key[1], key[0]))

    def _validate_locks(self, report, assignments, locks):
        indexed = {(str(_get(a, "employee_id")), _day(a)): a for a in assignments}
        for lock in locks:
            key = (str(_get(lock, "employee_id")), _day(lock))
            actual = indexed.get(key)
            fields = _get(lock, "fields", None) or ("working", "shift_type", "duty_station", "primary_role", "special_role")
            mismatches = [name for name in fields if actual is None or _get(actual, name) != _get(lock, name)]
            if mismatches:
                report.issues.append(ValidationIssue("locked_decision", "Locked decision was removed or changed", key[1], key[0], details={"fields": mismatches}))

    def _validate_requirements(self, report, by_date, employees, requirements):
        for req in requirements:
            day = _day(req)
            daily = by_date.get(day, [])
            station = _get(req, "station")
            shift = _get(req, "shift_type")
            role = _get(req, "special_role") or _get(req, "role")
            qualification = _get(req, "qualification")
            required = int(_get(req, "required_count", _get(req, "minimum", 0)))
            candidates = daily
            if station: candidates = [a for a in candidates if _get(a, "duty_station") == station]
            if shift: candidates = [a for a in candidates if _get(a, "shift_type") == shift]
            if role: candidates = [a for a in candidates if _get(a, "special_role") == role or _get(a, "primary_role") == role]
            if qualification:
                candidates = [a for a in candidates if qualification in set(_get(employees.get(str(_get(a, "employee_id")), {}), "qualifications", ())) ]
            actual = len(candidates)
            if actual < required:
                category = "qualification_coverage" if qualification else "special_role" if role else "station_requirement" if station else "weekday_coverage"
                label = qualification or role or station or shift or _get(req, "name", "coverage")
                report.issues.append(ValidationIssue(category, f"{label} requires {required}; {actual} assigned", day, requirement=str(label), expected=required, actual=actual))

    def _validate_budgets(self, report, by_date, budgets):
        for budget in budgets:
            if _get(budget, "behavior", "HARD_LIMIT") != "HARD_LIMIT":
                continue
            day = _day(budget)
            actual = sum(float(_get(a, "paid_hours", 0)) for a in by_date.get(day, []))
            limit = float(_get(budget, "max_hours"))
            if actual > limit:
                report.issues.append(ValidationIssue("budget_limit", f"Worked hours {actual:g} exceed hard budget {limit:g}", day, expected=limit, actual=actual))


def validate_schedule(assignments: Iterable[Any], employees: Iterable[Any], requirements: Iterable[Any] = (), **kwargs: Any) -> ValidationReport:
    """Convenience entry point using standard full-time limits."""
    return ScheduleValidator().validate(assignments, employees, requirements, **kwargs)
