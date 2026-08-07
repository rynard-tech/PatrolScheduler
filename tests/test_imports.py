from pathlib import Path

from openpyxl import Workbook

from patrol_scheduler.imports import IdentityMatcher, SpreadsheetImporter
from patrol_scheduler.models import Employee, EmploymentType


def test_mapping_preview_preserves_notes_and_flags_missing_values(tmp_path: Path):
    path = tmp_path / "requests.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Person", "Comments"])
    sheet.append(["Taylor Example", "cannot work some mornings"])
    sheet.append([None, "unclassified note"])
    workbook.save(path)
    preview = SpreadsheetImporter().preview(
        path, {"name": "Person", "free_text_notes": "Comments"}, ["name"]
    )
    assert preview.records[0]["free_text_notes"] == "cannot work some mornings"
    assert any(issue.code == "MISSING_VALUE" for issue in preview.issues)


def test_identity_matching_never_fuzzy_merges():
    employee = Employee("e1", "Alex", "Smith", EmploymentType.FULL_TIME)
    matcher = IdentityMatcher([employee])
    assert matcher.match(1, None, " Alex   Smith ")[0] == employee
    matched, issue = matcher.match(2, None, "Alec Smith")
    assert matched is None
    assert issue.code == "UNRESOLVED_IDENTITY"
