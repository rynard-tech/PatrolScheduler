"""Preview-first importer for employee scheduling requests.

The importer deliberately knows nothing about a particular workbook layout.  A
``RequestSourceMapping`` is required for every import, and all mutations happen
through the explicit :meth:`EmployeeRequestImporter.approve` operation.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, replace
from difflib import SequenceMatcher
from enum import Enum
from typing import Iterable, Mapping, MutableMapping, Protocol, Sequence
from uuid import uuid4


WEEKDAYS = ("SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY")
WEEKDAY_ALIASES = {name: name for name in WEEKDAYS} | {name[:3]: name for name in WEEKDAYS}
CONTIGUOUS_PATTERNS = {
    "SUN-WED", "MON-THU", "TUE-FRI", "WED-SAT", "THU-SUN", "FRI-MON", "SAT-TUE"
}


class RestrictionClassification(str, Enum):
    HARD_UNAVAILABLE = "HARD_UNAVAILABLE"
    SOFT_PREFERENCE = "SOFT_PREFERENCE"
    INFORMATION_ONLY = "INFORMATION_ONLY"


class IdentityStatus(str, Enum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class EmployeeIdentity:
    id: str
    employee_number: str | None
    full_name: str


@dataclass(frozen=True)
class RankedColumnMapping:
    """Source columns keyed by their explicit, one-based rank."""

    columns: Mapping[int, str]


@dataclass(frozen=True)
class RequestSourceMapping:
    employee_id: str | None
    full_name: str | None
    starting_waves: RankedColumnMapping
    schedules: RankedColumnMapping
    split_weekdays: str | None
    night_ski_weekdays: RankedColumnMapping
    availability_note: str | None = None
    restriction_note: str | None = None


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    row_number: int
    field: str | None = None


@dataclass(frozen=True)
class FuzzyCandidate:
    employee_id: str
    employee_number: str | None
    full_name: str
    score: float


@dataclass(frozen=True)
class IdentityResolution:
    status: IdentityStatus
    employee_id: str | None = None
    method: str | None = None
    candidates: tuple[FuzzyCandidate, ...] = ()


@dataclass(frozen=True)
class RawRequestNote:
    kind: str
    text: str
    classification: RestrictionClassification | None = None
    review_comment: str | None = None


@dataclass(frozen=True)
class EmployeeRequestPreviewRecord:
    row_number: int
    source_employee_number: str | None
    source_full_name: str | None
    identity: IdentityResolution
    starting_wave_rankings: tuple[str, ...]
    schedule_rankings: tuple[str, ...]
    split_schedule_weekdays: tuple[str, ...]
    night_ski_weekday_rankings: tuple[str, ...]
    notes: tuple[RawRequestNote, ...]


@dataclass(frozen=True)
class ImportPreview:
    id: str
    records: tuple[EmployeeRequestPreviewRecord, ...]
    issues: tuple[ValidationIssue, ...]
    approved: bool = False
    committed: bool = False

    @property
    def is_valid(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class NormalizedEmployeeRequest:
    employee_id: str
    starting_wave_rankings: tuple[str, ...]
    schedule_rankings: tuple[str, ...]
    split_schedule_weekdays: tuple[str, ...]
    night_ski_weekday_rankings: tuple[str, ...]
    notes: tuple[RawRequestNote, ...]


class RequestRepository(Protocol):
    def save_requests(self, requests: Sequence[NormalizedEmployeeRequest]) -> None: ...


@dataclass
class InMemoryRequestRepository:
    requests: list[NormalizedEmployeeRequest] = field(default_factory=list)

    def save_requests(self, requests: Sequence[NormalizedEmployeeRequest]) -> None:
        self.requests.extend(requests)


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-zA-Z0-9]+", " ", value).casefold().split())


def _text(row: Mapping[str, object], column: str | None) -> str | None:
    if column is None or row.get(column) is None:
        return None
    value = str(row[column]).strip()
    return value or None


class EmployeeRequestImporter:
    """Create, review, classify, and explicitly approve request imports."""

    def __init__(
        self,
        employees: Iterable[EmployeeIdentity],
        known_wave_references: Iterable[str],
        repository: RequestRepository,
        *,
        fuzzy_threshold: float = 0.78,
        fuzzy_ambiguity_margin: float = 0.04,
    ) -> None:
        self._employees = tuple(employees)
        self._by_number = {
            employee.employee_number.strip().casefold(): employee
            for employee in self._employees if employee.employee_number
        }
        self._by_name: MutableMapping[str, list[EmployeeIdentity]] = {}
        for employee in self._employees:
            self._by_name.setdefault(normalize_name(employee.full_name), []).append(employee)
        self._waves = {wave.strip().casefold(): wave.strip() for wave in known_wave_references}
        self._repository = repository
        self._threshold = fuzzy_threshold
        self._margin = fuzzy_ambiguity_margin
        self._previews: dict[str, ImportPreview] = {}

    def preview(
        self,
        rows: Iterable[Mapping[str, object]],
        mapping: RequestSourceMapping,
        *,
        confirmed_fuzzy_matches: Mapping[str, str] | None = None,
    ) -> ImportPreview:
        self._validate_mapping(mapping)
        records: list[EmployeeRequestPreviewRecord] = []
        issues: list[ValidationIssue] = []
        confirmations = confirmed_fuzzy_matches or {}
        for row_number, row in enumerate(rows, start=2):
            number = _text(row, mapping.employee_id)
            name = _text(row, mapping.full_name)
            identity = self._resolve_identity(number, name, confirmations)
            waves = self._parse_rankings(row, mapping.starting_waves, row_number, "starting_waves", issues)
            schedules = self._parse_rankings(row, mapping.schedules, row_number, "schedules", issues)
            split_days = self._parse_weekday_list(_text(row, mapping.split_weekdays), row_number, "split_weekdays", issues)
            night_days = self._parse_rankings(row, mapping.night_ski_weekdays, row_number, "night_ski_weekdays", issues, weekdays=True)
            self._validate_waves(waves, row_number, issues)
            self._validate_schedules(schedules, split_days, row_number, issues)
            if identity.status is not IdentityStatus.RESOLVED:
                issues.append(ValidationIssue(
                    "AMBIGUOUS_IDENTITY" if identity.status is IdentityStatus.AMBIGUOUS else "UNRESOLVED_EMPLOYEE",
                    "Employee identity requires administrator resolution.", row_number, "identity",
                ))
            notes = tuple(
                RawRequestNote(kind, value)
                for kind, value in (
                    ("AVAILABILITY", _text(row, mapping.availability_note)),
                    ("RESTRICTION", _text(row, mapping.restriction_note)),
                ) if value
            )
            records.append(EmployeeRequestPreviewRecord(
                row_number, number, name, identity, waves, schedules, split_days, night_days, notes
            ))
        preview = ImportPreview(str(uuid4()), tuple(records), tuple(issues))
        self._previews[preview.id] = preview
        return preview

    def classify_restriction(
        self,
        preview_id: str,
        row_number: int,
        note_kind: str,
        classification: RestrictionClassification,
        *,
        review_comment: str | None = None,
    ) -> ImportPreview:
        """Record an administrator's explicit interpretation without parsing prose."""
        preview = self._get_open_preview(preview_id)
        found = False
        updated_records = []
        for record in preview.records:
            notes = []
            for note in record.notes:
                if record.row_number == row_number and note.kind == note_kind:
                    note = replace(note, classification=classification, review_comment=review_comment)
                    found = True
                notes.append(note)
            updated_records.append(replace(record, notes=tuple(notes)))
        if not found:
            raise KeyError(f"No {note_kind!r} note exists on source row {row_number}")
        updated = replace(preview, records=tuple(updated_records))
        self._previews[preview_id] = updated
        return updated

    def approve(self, preview_id: str) -> tuple[NormalizedEmployeeRequest, ...]:
        """Commit a valid preview. Calling this method is the approval audit event."""
        preview = self._get_open_preview(preview_id)
        if preview.issues:
            raise ValueError("Cannot approve a preview with validation issues")
        normalized = tuple(
            NormalizedEmployeeRequest(
                employee_id=record.identity.employee_id or "",
                starting_wave_rankings=record.starting_wave_rankings,
                schedule_rankings=record.schedule_rankings,
                split_schedule_weekdays=record.split_schedule_weekdays,
                night_ski_weekday_rankings=record.night_ski_weekday_rankings,
                notes=record.notes,
            ) for record in preview.records
        )
        self._repository.save_requests(normalized)
        self._previews[preview_id] = replace(preview, approved=True, committed=True)
        return normalized

    def _get_open_preview(self, preview_id: str) -> ImportPreview:
        preview = self._previews.get(preview_id)
        if preview is None:
            raise KeyError(f"Unknown preview {preview_id}")
        if preview.committed:
            raise ValueError("Preview has already been committed")
        return preview

    @staticmethod
    def _validate_mapping(mapping: RequestSourceMapping) -> None:
        if not mapping.employee_id and not mapping.full_name:
            raise ValueError("Mapping must include employee_id or full_name")
        for name, ranked in (("starting_waves", mapping.starting_waves), ("schedules", mapping.schedules), ("night_ski_weekdays", mapping.night_ski_weekdays)):
            ranks = sorted(ranked.columns)
            if any(not isinstance(rank, int) or rank < 1 for rank in ranks) or ranks != list(range(1, len(ranks) + 1)):
                raise ValueError(f"{name} rank columns must be contiguous and one-based")
            if len(set(ranked.columns.values())) != len(ranked.columns):
                raise ValueError(f"{name} maps the same source column more than once")

    def _resolve_identity(self, number: str | None, name: str | None, confirmations: Mapping[str, str]) -> IdentityResolution:
        if number and (employee := self._by_number.get(number.casefold())):
            return IdentityResolution(IdentityStatus.RESOLVED, employee.id, "EMPLOYEE_ID")
        normalized = normalize_name(name or "")
        exact = self._by_name.get(normalized, []) if normalized else []
        if len(exact) == 1:
            return IdentityResolution(IdentityStatus.RESOLVED, exact[0].id, "EXACT_NORMALIZED_NAME")
        if len(exact) > 1:
            return IdentityResolution(IdentityStatus.AMBIGUOUS, candidates=tuple(self._candidate(e, 1.0) for e in exact))
        candidates = sorted(
            (self._candidate(employee, SequenceMatcher(None, normalized, normalize_name(employee.full_name)).ratio()) for employee in self._employees),
            key=lambda candidate: candidate.score, reverse=True,
        )
        candidates = [candidate for candidate in candidates if candidate.score >= self._threshold]
        confirmation_key = number or normalized
        confirmed_id = confirmations.get(confirmation_key)
        if confirmed_id and any(candidate.employee_id == confirmed_id for candidate in candidates):
            return IdentityResolution(IdentityStatus.RESOLVED, confirmed_id, "ADMIN_CONFIRMED_FUZZY", tuple(candidates))
        if not candidates:
            return IdentityResolution(IdentityStatus.UNRESOLVED)
        ambiguous = len(candidates) > 1 and candidates[0].score - candidates[1].score <= self._margin
        return IdentityResolution(IdentityStatus.AMBIGUOUS if ambiguous else IdentityStatus.UNRESOLVED, candidates=tuple(candidates))

    @staticmethod
    def _candidate(employee: EmployeeIdentity, score: float) -> FuzzyCandidate:
        return FuzzyCandidate(employee.id, employee.employee_number, employee.full_name, round(score, 4))

    def _parse_rankings(self, row, ranked, row_number, field_name, issues, *, weekdays=False) -> tuple[str, ...]:
        values: list[str] = []
        saw_blank = False
        for rank, column in sorted(ranked.columns.items()):
            value = _text(row, column)
            if value is None:
                saw_blank = True
                continue
            if saw_blank:
                issues.append(ValidationIssue("MALFORMED_RANKING", f"Rank {rank} follows a blank rank.", row_number, field_name))
            normalized = self._weekday(value, row_number, field_name, issues) if weekdays else value.strip()
            if normalized:
                values.append(normalized)
        folded = [value.casefold() for value in values]
        if len(folded) != len(set(folded)):
            issues.append(ValidationIssue("DUPLICATE_RANKING", "A ranked choice appears more than once.", row_number, field_name))
        return tuple(values)

    def _parse_weekday_list(self, value, row_number, field_name, issues) -> tuple[str, ...]:
        if not value:
            return ()
        parts = [part.strip() for part in re.split(r"[,;/|]+", value) if part.strip()]
        days = tuple(filter(None, (self._weekday(part, row_number, field_name, issues) for part in parts)))
        if len(days) != len(set(days)):
            issues.append(ValidationIssue("DUPLICATE_WEEKDAY", "Split schedule repeats a weekday.", row_number, field_name))
        return days

    @staticmethod
    def _weekday(value, row_number, field_name, issues) -> str | None:
        normalized = re.sub(r"[^A-Z]", "", value.upper())
        day = WEEKDAY_ALIASES.get(normalized)
        if day is None:
            issues.append(ValidationIssue("INVALID_WEEKDAY", f"Invalid weekday: {value!r}.", row_number, field_name))
        return day

    def _validate_waves(self, waves, row_number, issues) -> None:
        for wave in waves:
            if wave.casefold() not in self._waves:
                issues.append(ValidationIssue("UNKNOWN_WAVE", f"Unknown starting wave: {wave!r}.", row_number, "starting_waves"))

    @staticmethod
    def _validate_schedules(schedules, split_days, row_number, issues) -> None:
        for schedule in schedules:
            canonical = schedule.upper().replace("–", "-").replace("—", "-").replace(" ", "")
            if canonical not in CONTIGUOUS_PATTERNS and canonical != "SPLIT":
                issues.append(ValidationIssue("INVALID_SCHEDULE_PATTERN", f"Invalid schedule pattern: {schedule!r}.", row_number, "schedules"))
        has_split = any(schedule.strip().upper() == "SPLIT" for schedule in schedules)
        if (has_split and len(split_days) != 4) or (split_days and len(split_days) != 4):
            issues.append(ValidationIssue("INVALID_SPLIT_PATTERN", "A split schedule must contain exactly four distinct weekdays.", row_number, "split_weekdays"))
        if split_days and not has_split:
            issues.append(ValidationIssue("INVALID_SPLIT_PATTERN", "Split weekdays were supplied but SPLIT is not ranked.", row_number, "split_weekdays"))
