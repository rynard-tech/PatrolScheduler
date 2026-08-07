"""Deterministic reference-data seeds; operational counts belong in requirement data."""

from datetime import time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import DutyStation, ShiftCode, ShiftType

STATIONS = {
    "DERCUM": "Dercum",
    "NORTH_PEAK": "North Peak",
    "OUTBACK": "Outback",
    "BERGMAN": "Bergman",
}


def seed_reference_data(session: Session) -> None:
    existing_stations = set(session.scalars(select(DutyStation.canonical_code)))
    session.add_all(
        DutyStation(canonical_code=code, display_label=label)
        for code, label in STATIONS.items()
        if code not in existing_stations
    )
    if session.scalar(select(ShiftType).where(ShiftType.code == ShiftCode.STANDARD)) is None:
        session.add(
            ShiftType(
                code=ShiftCode.STANDARD,
                display_name="Standard",
                start_time=time(7, 15),
                end_time=time(17, 15),
                paid_hours=Decimal("10.00"),
            )
        )
    session.commit()
