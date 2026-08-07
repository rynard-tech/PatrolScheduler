from patrol_scheduler.imports import EmployeeMatcher, SourceMapping
from patrol_scheduler.models import Employee


def test_matching_prefers_id_then_exact_normalized_name():
    employees = [Employee("1", "Ada", "Lovelace", employee_number="100")]
    matcher = EmployeeMatcher(employees)
    preview = matcher.preview(
        [
            {"number": "100", "name": "Wrong Name"},
            {"number": "", "name": "  ADA   LOVELACE "},
        ],
        SourceMapping("number", "name"),
    )
    assert [row.employee_id for row in preview.rows] == ["1", "1"]
    assert preview.counts["matched"] == 2


def test_fuzzy_name_is_never_silently_merged():
    matcher = EmployeeMatcher([Employee("1", "Katherine", "Johnson")])
    preview = matcher.preview(
        [{"name": "Katrine Johnson"}], SourceMapping(None, "name")
    )
    row = preview.rows[0]
    assert row.status == "UNRESOLVED"
    assert row.employee_id is None
    assert row.candidate_ids == ("1",)
