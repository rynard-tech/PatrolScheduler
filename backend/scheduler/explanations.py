"""Stable, truthful presentation of validation and feasibility findings."""

from __future__ import annotations

from typing import Any


RESOLUTION_CATEGORIES = {
    "insufficient_supervisors": ("add_part_time_coverage", "activate_qualified_employee", "change_work_pattern", "modify_staffing_requirement"),
    "insufficient_qualification_holders": ("activate_qualified_employee", "add_part_time_coverage", "modify_staffing_requirement"),
    "hard_budget_below_minimum_staffing": ("modify_hard_budget", "modify_staffing_requirement"),
    "approved_absence_conflicts": ("add_part_time_coverage", "change_work_pattern", "approve_explicit_override"),
    "locked_assignments": ("unlock_assignment", "modify_staffing_requirement", "approve_explicit_override"),
}


def possible_resolutions(category: str) -> list[str]:
    """Return options for an administrator; no option is selected or applied."""
    return list(RESOLUTION_CATEGORIES.get(category, ("add_part_time_coverage", "modify_staffing_requirement", "approve_explicit_override")))


def explain_conflict(conflict: Any) -> str:
    category = conflict.get("category") if isinstance(conflict, dict) else conflict.category
    labels = {
        "insufficient_supervisors": "There are not enough available supervisors for the configured coverage.",
        "insufficient_qualification_holders": "There are not enough available qualification holders for the configured requirement.",
        "hard_budget_below_minimum_staffing": "The hard budget cannot fund the configured minimum staffing.",
        "approved_absence_conflicts": "Approved absences reduce coverage below a configured hard requirement.",
        "locked_assignments": "Locked decisions contradict another hard requirement.",
    }
    return labels.get(category, "The configured hard inputs are contradictory; administrative review is required.")
