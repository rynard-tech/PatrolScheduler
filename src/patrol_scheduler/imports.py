from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Iterable, Mapping

from .models import Employee


def normalize_name(value: str) -> str:
    return " ".join(value.casefold().replace(",", " ").split())


@dataclass(frozen=True)
class SourceMapping:
    employee_id_column: str | None
    employee_name_column: str
    field_columns: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ImportRowPreview:
    row_number: int
    status: str
    source_name: str
    employee_id: str | None = None
    candidate_ids: tuple[str, ...] = ()


@dataclass
class ImportPreview:
    rows: list[ImportRowPreview]

    @property
    def counts(self) -> dict[str, int]:
        statuses = ("MATCHED", "NEW", "UNRESOLVED", "AMBIGUOUS")
        return {
            status.lower(): sum(row.status == status for row in self.rows)
            for status in statuses
        }


class EmployeeMatcher:
    """ID/exact matching plus review-only fuzzy suggestions.

    A fuzzy candidate is never returned as a match; an administrator must confirm it.
    """

    def __init__(self, employees: Iterable[Employee], fuzzy_threshold: float = 0.78):
        self.employees = list(employees)
        self.by_number = {
            e.employee_number: e for e in self.employees if e.employee_number
        }
        self.by_name: dict[str, list[Employee]] = {}
        for employee in self.employees:
            self.by_name.setdefault(normalize_name(employee.display_name), []).append(
                employee
            )
            self.by_name.setdefault(
                normalize_name(f"{employee.last_name} {employee.first_name}"), []
            ).append(employee)
        self.fuzzy_threshold = fuzzy_threshold

    def preview(
        self, rows: Iterable[Mapping[str, object]], mapping: SourceMapping
    ) -> ImportPreview:
        previews = []
        for row_number, row in enumerate(rows, start=2):
            source_name = str(row.get(mapping.employee_name_column, "")).strip()
            source_number = (
                str(row.get(mapping.employee_id_column, "")).strip()
                if mapping.employee_id_column
                else ""
            )
            if source_number and source_number in self.by_number:
                previews.append(
                    ImportRowPreview(
                        row_number,
                        "MATCHED",
                        source_name,
                        self.by_number[source_number].id,
                    )
                )
                continue
            exact = {
                employee.id: employee
                for employee in self.by_name.get(normalize_name(source_name), [])
            }
            if len(exact) == 1:
                previews.append(
                    ImportRowPreview(
                        row_number, "MATCHED", source_name, next(iter(exact))
                    )
                )
                continue
            if len(exact) > 1:
                previews.append(
                    ImportRowPreview(
                        row_number,
                        "AMBIGUOUS",
                        source_name,
                        candidate_ids=tuple(sorted(exact)),
                    )
                )
                continue
            candidates = sorted(
                (
                    (
                        SequenceMatcher(
                            None,
                            normalize_name(source_name),
                            normalize_name(employee.display_name),
                        ).ratio(),
                        employee.id,
                    )
                    for employee in self.employees
                ),
                reverse=True,
            )
            suggestions = tuple(
                employee_id
                for score, employee_id in candidates[:3]
                if score >= self.fuzzy_threshold
            )
            status = "UNRESOLVED" if suggestions else "NEW"
            previews.append(
                ImportRowPreview(
                    row_number, status, source_name, candidate_ids=suggestions
                )
            )
        return ImportPreview(previews)
