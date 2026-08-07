from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from typing import Any

@dataclass(frozen=True)
class Person:
    id:int; name:str; employment_type:str="FULL_TIME"; supervisor:bool=False; manager:bool=False; rookie:bool=False; qualifications:frozenset[str]=frozenset(); pattern:tuple[int,...]=(); available_dates:frozenset[date]|None=None; history:dict[str,int]=field(default_factory=dict); preferences:tuple[tuple[int,...],...]=(); family_id:int|None=None
@dataclass(frozen=True)
class StationRule:
    code:str; minimum:int; qualification_minimums:dict[str,int]=field(default_factory=dict)
@dataclass(frozen=True)
class ShiftRule:
    code:str; count:int; supervisor_count:int=0; eligibility:str|None=None
@dataclass(frozen=True)
class Rules:
    ft_shifts:int=4; manager_shifts:int=5; hours_per_shift:int=10; max_ft_hours:int=40; max_station_repeats:int=2; stations:tuple[StationRule,...]=(); specialty_shifts:tuple[ShiftRule,...]=(); budget_hours:int|None=None; budget_hard:bool=True
@dataclass(frozen=True)
class Lock:
    employee_id:int; day:int; station:str|None=None; shift:str|None=None
@dataclass
class Problem:
    week_start:date; people:list[Person]; rules:Rules; locks:list[Lock]=field(default_factory=list); approved_absences:set[tuple[int,int]]=field(default_factory=set)
@dataclass
class Assignment:
    employee_id:int; employee_name:str; date:date; station:str; shift_type:str; paid_hours:int; role:str
@dataclass
class SolveResult:
    status:str; assignments:list[Assignment]=field(default_factory=list); conflicts:list[dict[str,Any]]=field(default_factory=list); metrics:dict[str,Any]=field(default_factory=dict)
    def to_dict(self): return {"status":self.status,"assignments":[{**asdict(a),"date":a.date.isoformat()} for a in self.assignments],"conflicts":self.conflicts,"metrics":self.metrics}
