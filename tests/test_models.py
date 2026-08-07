from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import create_database_engine, initialize_schema
from backend.models import DutyStation, Season, ShiftCode, ShiftType
from backend.seeds import STATIONS, seed_reference_data


@pytest.fixture
def engine():
    value = create_database_engine("sqlite:///:memory:")
    initialize_schema(value)
    return value


def test_season_defaults_are_configurable(engine):
    with Session(engine) as session:
        season = Season(name="2026-27", start_date=date(2026, 10, 1), end_date=date(2027, 4, 30))
        session.add(season)
        session.commit()
        session.refresh(season)
        assert season.normal_shifts_per_week == 4
        assert season.paid_hours_per_worked_shift == Decimal("10.00")
        assert season.max_weekly_worked_hours == Decimal("40.00")


def test_reference_seed_is_idempotent_and_has_no_staffing_counts(engine):
    with Session(engine) as session:
        seed_reference_data(session)
        seed_reference_data(session)
        assert session.scalar(select(func.count()).select_from(DutyStation)) == 4
        assert set(session.scalars(select(DutyStation.canonical_code))) == set(STATIONS)
        standard = session.scalar(select(ShiftType).where(ShiftType.code == ShiftCode.STANDARD))
        assert standard is not None and standard.paid_hours == Decimal("10.00")


def test_sqlite_foreign_keys_are_enforced(engine):
    from backend.models import EmployeeQualification

    with Session(engine) as session:
        session.add(EmployeeQualification(employee_id=999, qualification_id=999))
        with pytest.raises(IntegrityError):
            session.commit()
