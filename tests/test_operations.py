from datetime import date

from backend.models.operations import DutyStation, RequirementStrength, SpecialRoleRequirement, full_operations_requirement_set


def test_full_operations_counts_are_seed_data():
    seeded = full_operations_requirement_set()
    stations = {item.station: item for item in seeded.station_requirements}
    assert stations[DutyStation.BERGMAN].minimum_staff == 7
    assert stations[DutyStation.OUTBACK].qualification_counts["AVALANCHE_ROUTE_LEADER"] == 2
    assert stations[DutyStation.NORTH_PEAK].qualification_counts["TEAM_LEAD"] == 1
    assert stations[DutyStation.DERCUM].minimum_staff == 0
    assert seeded.remainder_station == DutyStation.DERCUM


def test_role_date_and_weekday_applicability_is_generic():
    requirement = SpecialRoleRequirement(
        "custom", "FUTURE_ROLE", 2, RequirementStrength.SOFT,
        start_date=date(2026, 1, 5), end_date=date(2026, 1, 12),
        weekdays=frozenset({0}), required_station=DutyStation.DERCUM,
        preferred_employee_ids=("employee-a",), backup_employee_ids=("employee-b",),
    )
    assert requirement.applies_on(date(2026, 1, 5))
    assert requirement.applies_on(date(2026, 1, 12))
    assert not requirement.applies_on(date(2026, 1, 6))
