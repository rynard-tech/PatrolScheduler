from datetime import date, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .enums import EmploymentType, PaidStatusType, RuleStrength, ShiftCode, Weekday


def enum_type(enum: type, name: str) -> Enum:
    return Enum(enum, name=name, native_enum=False, validate_strings=True)


class SchemaVersion(Base):
    __tablename__ = "schema_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)


class Season(TimestampMixin, Base):
    __tablename__ = "seasons"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="valid_dates"),
        CheckConstraint("normal_shifts_per_week > 0", name="positive_shifts"),
        CheckConstraint("paid_hours_per_worked_shift > 0", name="positive_shift_hours"),
        CheckConstraint("max_weekly_worked_hours > 0", name="positive_weekly_hours"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    normal_shifts_per_week: Mapped[int] = mapped_column(default=4)
    paid_hours_per_worked_shift: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=10)
    max_weekly_worked_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=40)


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_number: Mapped[str | None] = mapped_column(String(64), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    display_name: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    employment_type: Mapped[EmploymentType] = mapped_column(
        enum_type(EmploymentType, "employment_type")
    )
    supervisor_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    manager_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    prior_winter_hours: Mapped[Decimal] = mapped_column(Numeric(9, 2), default=0)
    calculated_seniority_rank: Mapped[int | None]
    manual_seniority_override: Mapped[int | None]
    notes: Mapped[str | None] = mapped_column(Text)


class Qualification(TimestampMixin, Base):
    __tablename__ = "qualifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    display_name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)


class EmployeeQualification(Base):
    __tablename__ = "employee_qualifications"
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), primary_key=True)
    qualification_id: Mapped[int] = mapped_column(ForeignKey("qualifications.id"), primary_key=True)
    effective_date: Mapped[date | None] = mapped_column(Date)
    expiration_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)


class WorkPattern(TimestampMixin, Base):
    __tablename__ = "work_patterns"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    display_name: Mapped[str] = mapped_column(String(160))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    weekdays: Mapped[list["WorkPatternWeekday"]] = relationship(
        back_populates="work_pattern",
        cascade="all, delete-orphan",
        order_by="WorkPatternWeekday.position",
    )


class WorkPatternWeekday(Base):
    __tablename__ = "work_pattern_weekdays"
    __table_args__ = (UniqueConstraint("work_pattern_id", "weekday"),)
    work_pattern_id: Mapped[int] = mapped_column(ForeignKey("work_patterns.id"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    weekday: Mapped[Weekday] = mapped_column(enum_type(Weekday, "weekday"))
    work_pattern: Mapped[WorkPattern] = relationship(back_populates="weekdays")


class PatternPreference(Base):
    __tablename__ = "pattern_preferences"
    __table_args__ = (UniqueConstraint("season_id", "employee_id", "rank"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    work_pattern_id: Mapped[int] = mapped_column(ForeignKey("work_patterns.id"))
    rank: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)


class PaidStatusRecord(TimestampMixin, Base):
    __tablename__ = "paid_status_records"
    __table_args__ = (
        CheckConstraint("paid_hours >= 0", name="nonnegative_hours"),
        UniqueConstraint("employee_id", "status_date", "status_type"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    status_date: Mapped[date] = mapped_column(Date)
    status_type: Mapped[PaidStatusType] = mapped_column(
        enum_type(PaidStatusType, "paid_status_type")
    )
    paid_hours: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    notes: Mapped[str | None] = mapped_column(Text)


class StaffingWave(TimestampMixin, Base):
    __tablename__ = "staffing_waves"
    __table_args__ = (UniqueConstraint("season_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    name: Mapped[str] = mapped_column(String(120))
    effective_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    target_people_per_day: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    target_paid_hours_per_day: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    approximate_required_active_ft: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    max_budgeted_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    notes: Mapped[str | None] = mapped_column(Text)


class StaffingWavePreference(Base):
    __tablename__ = "staffing_wave_preferences"
    __table_args__ = (UniqueConstraint("employee_id", "season_id", "rank"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    staffing_wave_id: Mapped[int] = mapped_column(ForeignKey("staffing_waves.id"))
    rank: Mapped[int] = mapped_column(Integer)


class StaffingWaveParticipant(Base):
    __tablename__ = "staffing_wave_participants"
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), primary_key=True)
    staffing_wave_id: Mapped[int] = mapped_column(ForeignKey("staffing_waves.id"), primary_key=True)
    awarded: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)


class RequirementSet(TimestampMixin, Base):
    __tablename__ = "requirement_sets"
    __table_args__ = (CheckConstraint("end_date >= start_date", name="valid_dates"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    name: Mapped[str] = mapped_column(String(160))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    max_budgeted_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    night_ski_active: Mapped[bool] = mapped_column(Boolean, default=False)
    first_tracks_active: Mapped[bool] = mapped_column(Boolean, default=False)


class DutyStation(TimestampMixin, Base):
    __tablename__ = "duty_stations"
    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_code: Mapped[str] = mapped_column(String(80), unique=True)
    display_label: Mapped[str] = mapped_column(String(160))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class StationStaffingRequirement(Base):
    __tablename__ = "station_staffing_requirements"
    __table_args__ = (UniqueConstraint("requirement_set_id", "duty_station_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    requirement_set_id: Mapped[int] = mapped_column(ForeignKey("requirement_sets.id"))
    duty_station_id: Mapped[int] = mapped_column(ForeignKey("duty_stations.id"))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    minimum_staff: Mapped[int] = mapped_column(default=0)
    target_staff: Mapped[int | None]
    strength: Mapped[RuleStrength] = mapped_column(
        enum_type(RuleStrength, "rule_strength"), default=RuleStrength.HARD
    )


class ShiftType(TimestampMixin, Base):
    __tablename__ = "shift_types"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[ShiftCode] = mapped_column(enum_type(ShiftCode, "shift_code"), unique=True)
    display_name: Mapped[str] = mapped_column(String(160))
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    paid_hours: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    active_start_date: Mapped[date | None] = mapped_column(Date)
    active_end_date: Mapped[date | None] = mapped_column(Date)


class SpecialRoleRequirement(TimestampMixin, Base):
    __tablename__ = "special_role_requirements"
    id: Mapped[int] = mapped_column(primary_key=True)
    requirement_set_id: Mapped[int] = mapped_column(ForeignKey("requirement_sets.id"))
    role_code: Mapped[str] = mapped_column(String(100))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    required_count: Mapped[int] = mapped_column(default=1)
    required_station_id: Mapped[int | None] = mapped_column(ForeignKey("duty_stations.id"))
    required_shift_type_id: Mapped[int | None] = mapped_column(ForeignKey("shift_types.id"))
    eligibility_qualification_id: Mapped[int | None] = mapped_column(
        ForeignKey("qualifications.id")
    )
    strength: Mapped[RuleStrength] = mapped_column(
        enum_type(RuleStrength, "special_role_strength"), default=RuleStrength.HARD
    )
    notes: Mapped[str | None] = mapped_column(Text)


class SpecialRoleWeekday(Base):
    __tablename__ = "special_role_weekdays"
    special_role_requirement_id: Mapped[int] = mapped_column(
        ForeignKey("special_role_requirements.id"), primary_key=True
    )
    weekday: Mapped[Weekday] = mapped_column(
        enum_type(Weekday, "special_role_weekday"), primary_key=True
    )
