"""Normalized persistence schema. Solver policy is stored in rows, not this module."""
from datetime import date, datetime, time
from enum import StrEnum
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase): pass
class EmploymentType(StrEnum): FULL_TIME="FULL_TIME"; PART_TIME="PART_TIME"; MANAGER="MANAGER"
class RuleStrength(StrEnum): HARD="HARD"; SOFT="SOFT"; INFORMATIONAL="INFORMATIONAL"

class Season(Base):
    __tablename__="seasons"; id: Mapped[int]=mapped_column(primary_key=True); name: Mapped[str]=mapped_column(String(40), unique=True); start_date: Mapped[date]=mapped_column(Date); end_date: Mapped[date]=mapped_column(Date); settings: Mapped[dict]=mapped_column(JSON, default=dict)
class Employee(Base):
    __tablename__="employees"; id: Mapped[int]=mapped_column(primary_key=True); season_id: Mapped[int]=mapped_column(ForeignKey("seasons.id")); employee_number: Mapped[str|None]=mapped_column(String(40)); first_name: Mapped[str]=mapped_column(String(80)); last_name: Mapped[str]=mapped_column(String(80)); display_name: Mapped[str]=mapped_column(String(170)); active: Mapped[bool]=mapped_column(Boolean, default=True); employment_type: Mapped[str]=mapped_column(String(20)); supervisor_flag: Mapped[bool]=mapped_column(Boolean, default=False); manager_flag: Mapped[bool]=mapped_column(Boolean, default=False); rookie_status: Mapped[str]=mapped_column(String(20), default="GRADUATED"); prior_winter_hours: Mapped[float]=mapped_column(Float, default=0); seniority_rank: Mapped[int|None]=mapped_column(Integer); active_start_date: Mapped[date|None]=mapped_column(Date); active_end_date: Mapped[date|None]=mapped_column(Date); notes: Mapped[str|None]=mapped_column(Text)
    __table_args__=(UniqueConstraint("season_id","employee_number"),)
class Qualification(Base):
    __tablename__="qualifications"; id: Mapped[int]=mapped_column(primary_key=True); code: Mapped[str]=mapped_column(String(80), unique=True); name: Mapped[str]=mapped_column(String(120))
class EmployeeQualification(Base):
    __tablename__="employee_qualifications"; employee_id: Mapped[int]=mapped_column(ForeignKey("employees.id"), primary_key=True); qualification_id: Mapped[int]=mapped_column(ForeignKey("qualifications.id"), primary_key=True); valid_from: Mapped[date|None]=mapped_column(Date); valid_until: Mapped[date|None]=mapped_column(Date)
class RankedPreference(Base):
    __tablename__="ranked_preferences"; id: Mapped[int]=mapped_column(primary_key=True); employee_id: Mapped[int]=mapped_column(ForeignKey("employees.id")); category: Mapped[str]=mapped_column(String(40)); value: Mapped[str]=mapped_column(String(120)); rank: Mapped[int]=mapped_column(Integer); raw_value: Mapped[str|None]=mapped_column(Text)
class StaffingWave(Base):
    __tablename__="staffing_waves"; id: Mapped[int]=mapped_column(primary_key=True); season_id: Mapped[int]=mapped_column(ForeignKey("seasons.id")); name: Mapped[str]=mapped_column(String(80)); effective_date: Mapped[date]=mapped_column(Date); end_date: Mapped[date|None]=mapped_column(Date); target_people_per_day: Mapped[float]=mapped_column(Float); max_budgeted_hours: Mapped[float|None]=mapped_column(Float); configuration: Mapped[dict]=mapped_column(JSON, default=dict)
class WorkPattern(Base):
    __tablename__="work_patterns"; id: Mapped[int]=mapped_column(primary_key=True); season_id: Mapped[int]=mapped_column(ForeignKey("seasons.id")); name: Mapped[str]=mapped_column(String(80)); weekdays: Mapped[list]=mapped_column(JSON); shifts_per_week: Mapped[int]=mapped_column(Integer); is_manager_exception: Mapped[bool]=mapped_column(Boolean, default=False)
class OperatingPeriod(Base):
    __tablename__="operating_periods"; id: Mapped[int]=mapped_column(primary_key=True); season_id: Mapped[int]=mapped_column(ForeignKey("seasons.id")); name: Mapped[str]=mapped_column(String(80)); start_date: Mapped[date]=mapped_column(Date); end_date: Mapped[date]=mapped_column(Date); budget_hours: Mapped[float|None]=mapped_column(Float); budget_strength: Mapped[str]=mapped_column(String(20), default="TARGET")
class Station(Base):
    __tablename__="stations"; id: Mapped[int]=mapped_column(primary_key=True); code: Mapped[str]=mapped_column(String(40), unique=True); display_name: Mapped[str]=mapped_column(String(80)); enabled: Mapped[bool]=mapped_column(Boolean, default=True)
class ShiftType(Base):
    __tablename__="shift_types"; id: Mapped[int]=mapped_column(primary_key=True); code: Mapped[str]=mapped_column(String(40), unique=True); display_name: Mapped[str]=mapped_column(String(80)); start_time: Mapped[time]=mapped_column(Time); end_time: Mapped[time]=mapped_column(Time); paid_hours: Mapped[float]=mapped_column(Float); eligibility_qualification: Mapped[str|None]=mapped_column(String(80))
class Requirement(Base):
    __tablename__="requirements"; id: Mapped[int]=mapped_column(primary_key=True); operating_period_id: Mapped[int]=mapped_column(ForeignKey("operating_periods.id")); kind: Mapped[str]=mapped_column(String(40)); station_id: Mapped[int|None]=mapped_column(ForeignKey("stations.id")); shift_type_id: Mapped[int|None]=mapped_column(ForeignKey("shift_types.id")); qualification_code: Mapped[str|None]=mapped_column(String(80)); required_count: Mapped[int]=mapped_column(Integer); strength: Mapped[str]=mapped_column(String(20)); weekdays: Mapped[list]=mapped_column(JSON, default=list); configuration: Mapped[dict]=mapped_column(JSON, default=dict)
class Family(Base):
    __tablename__="families"; id: Mapped[int]=mapped_column(primary_key=True); season_id: Mapped[int]=mapped_column(ForeignKey("seasons.id")); name: Mapped[str]=mapped_column(String(80)); supervisor_employee_id: Mapped[int]=mapped_column(ForeignKey("employees.id"))
class FamilyMembership(Base):
    __tablename__="family_memberships"; family_id: Mapped[int]=mapped_column(ForeignKey("families.id"), primary_key=True); employee_id: Mapped[int]=mapped_column(ForeignKey("employees.id"), primary_key=True); active_start: Mapped[date|None]=mapped_column(Date); active_end: Mapped[date|None]=mapped_column(Date)
class Availability(Base):
    __tablename__="availability"; id: Mapped[int]=mapped_column(primary_key=True); employee_id: Mapped[int]=mapped_column(ForeignKey("employees.id")); date: Mapped[date]=mapped_column(Date); available: Mapped[bool]=mapped_column(Boolean); status: Mapped[str]=mapped_column(String(30)); preferred: Mapped[bool]=mapped_column(Boolean, default=False); requested_assignment: Mapped[str|None]=mapped_column(String(120)); raw_notes: Mapped[str|None]=mapped_column(Text)
class EmployeeSeasonHistory(Base):
    __tablename__="employee_season_history"; id: Mapped[int]=mapped_column(primary_key=True); employee_id: Mapped[int]=mapped_column(ForeignKey("employees.id")); season_id: Mapped[int]=mapped_column(ForeignKey("seasons.id")); station_counts: Mapped[dict]=mapped_column(JSON, default=dict); shift_counts: Mapped[dict]=mapped_column(JSON, default=dict); recent_station_sequence: Mapped[list]=mapped_column(JSON, default=list); relationship_exposure: Mapped[dict]=mapped_column(JSON, default=dict)
class Assignment(Base):
    __tablename__="assignments"; id: Mapped[int]=mapped_column(primary_key=True); employee_id: Mapped[int]=mapped_column(ForeignKey("employees.id")); date: Mapped[date]=mapped_column(Date); working: Mapped[bool]=mapped_column(Boolean); shift_type_id: Mapped[int|None]=mapped_column(ForeignKey("shift_types.id")); station_id: Mapped[int|None]=mapped_column(ForeignKey("stations.id")); paid_hours: Mapped[float]=mapped_column(Float, default=0); primary_role: Mapped[str|None]=mapped_column(String(80)); generated_by_solver: Mapped[bool]=mapped_column(Boolean, default=True); notes: Mapped[str|None]=mapped_column(Text); __table_args__=(UniqueConstraint("employee_id","date"),)
class AssignmentLock(Base):
    __tablename__="assignment_locks"; id: Mapped[int]=mapped_column(primary_key=True); assignment_id: Mapped[int|None]=mapped_column(ForeignKey("assignments.id")); employee_id: Mapped[int]=mapped_column(ForeignKey("employees.id")); date: Mapped[date|None]=mapped_column(Date); scope: Mapped[str]=mapped_column(String(30)); value: Mapped[str|None]=mapped_column(String(120)); created_by: Mapped[str]=mapped_column(String(120)); created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
class Override(Base):
    __tablename__="overrides"; id: Mapped[int]=mapped_column(primary_key=True); employee_id: Mapped[int|None]=mapped_column(ForeignKey("employees.id")); date: Mapped[date|None]=mapped_column(Date); rule_code: Mapped[str]=mapped_column(String(80)); reason: Mapped[str]=mapped_column(Text); previous_state: Mapped[dict]=mapped_column(JSON); new_state: Mapped[dict]=mapped_column(JSON); created_by: Mapped[str]=mapped_column(String(120)); created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
