import pytest

from backend.imports.requests_importer import (
    EmployeeIdentity, EmployeeRequestImporter, IdentityStatus,
    InMemoryRequestRepository, RankedColumnMapping, RequestSourceMapping,
    RestrictionClassification,
)


def mapping():
    return RequestSourceMapping(
        employee_id="number", full_name="name",
        starting_waves=RankedColumnMapping({1: "wave_1", 2: "wave_2"}),
        schedules=RankedColumnMapping({1: "schedule_1", 2: "schedule_2"}),
        split_weekdays="split",
        night_ski_weekdays=RankedColumnMapping({1: "night_1", 2: "night_2"}),
        availability_note="availability", restriction_note="restriction",
    )


@pytest.fixture
def setup_importer():
    repository = InMemoryRequestRepository()
    importer = EmployeeRequestImporter(
        [EmployeeIdentity("e1", "100", "José Smith"), EmployeeIdentity("e2", "200", "Jane Doe")],
        ["Wave A", "Wave B"], repository,
    )
    return importer, repository


def valid_row(**changes):
    row = {"number": "100", "name": "ignored", "wave_1": "Wave B", "wave_2": "Wave A",
           "schedule_1": "SPLIT", "schedule_2": "Sun-Wed", "split": "Mon, Wed, Fri, Sat",
           "night_1": "Friday", "night_2": "Tue", "availability": "Prefer mornings",
           "restriction": "Cannot always drive after dark"}
    row.update(changes)
    return row


def test_preserves_rankings_notes_and_requires_explicit_approval(setup_importer):
    importer, repository = setup_importer
    preview = importer.preview([valid_row()], mapping())
    assert preview.is_valid
    record = preview.records[0]
    assert record.starting_wave_rankings == ("Wave B", "Wave A")
    assert record.night_ski_weekday_rankings == ("FRIDAY", "TUESDAY")
    assert record.split_schedule_weekdays == ("MONDAY", "WEDNESDAY", "FRIDAY", "SATURDAY")
    assert record.notes[1].classification is None
    assert repository.requests == []

    importer.classify_restriction(preview.id, 2, "RESTRICTION", RestrictionClassification.INFORMATION_ONLY)
    committed = importer.approve(preview.id)
    assert committed[0].notes[1].classification is RestrictionClassification.INFORMATION_ONLY
    assert repository.requests == list(committed)
    with pytest.raises(ValueError, match="already"):
        importer.approve(preview.id)


def test_identity_order_and_confirmed_fuzzy_match(setup_importer):
    importer, _ = setup_importer
    by_id = importer.preview([valid_row(name="Someone Else")], mapping())
    assert by_id.records[0].identity.method == "EMPLOYEE_ID"
    exact = importer.preview([valid_row(number="", name="Jose Smith")], mapping())
    assert exact.records[0].identity.method == "EXACT_NORMALIZED_NAME"
    fuzzy = importer.preview([valid_row(number="", name="Jsoe Smith")], mapping())
    assert fuzzy.records[0].identity.status is IdentityStatus.UNRESOLVED
    assert fuzzy.records[0].identity.candidates
    confirmed = importer.preview([valid_row(number="", name="Jsoe Smith")], mapping(), confirmed_fuzzy_matches={"jsoe smith": "e1"})
    assert confirmed.records[0].identity.method == "ADMIN_CONFIRMED_FUZZY"


def test_validation_blocks_commit_and_reports_data_problems(setup_importer):
    importer, repository = setup_importer
    preview = importer.preview([valid_row(
        number="999", name="Nobody", wave_1="Missing", wave_2="Missing",
        schedule_1="SPLIT", schedule_2="", split="Monday, Monday, Funday",
        night_1="Moonday", night_2="Friday",
    )], mapping())
    codes = {issue.code for issue in preview.issues}
    assert {"UNRESOLVED_EMPLOYEE", "UNKNOWN_WAVE", "DUPLICATE_RANKING", "INVALID_WEEKDAY", "INVALID_SPLIT_PATTERN"} <= codes
    with pytest.raises(ValueError, match="validation issues"):
        importer.approve(preview.id)
    assert repository.requests == []


def test_rank_mapping_must_be_explicit_and_contiguous(setup_importer):
    importer, _ = setup_importer
    bad = mapping()
    bad = RequestSourceMapping(**{**bad.__dict__, "schedules": RankedColumnMapping({1: "first", 3: "third"})})
    with pytest.raises(ValueError, match="contiguous"):
        importer.preview([], bad)
