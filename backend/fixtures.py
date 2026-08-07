"""Deterministic, wholly synthetic seven-day operating fixture."""
from datetime import date
from .scheduler.types import Person, Problem, Rules, ShiftRule, StationRule

def synthetic_problem(week_start:date=date(2026,1,4)) -> Problem:
    people=[]
    for i in range(28):
        pattern=tuple((i+j)%7 for j in range(4)); supervisor=i<14
        quals={"PATROLLER","FIRST_TRACKS","NIGHT_SKI"}
        if supervisor: quals|={"SUPERVISOR","ROUTE_LEADER","TEAM_LEAD"}
        people.append(Person(i+1,f"Patroller {i+1:02d}",supervisor=supervisor,rookie=i>=26,qualifications=frozenset(quals),pattern=pattern,history={"DERCUM":i%4,"NORTH_PEAK":(i+1)%4,"OUTBACK":(i+2)%4,"BERGMAN":(i+3)%4},preferences=(pattern,),family_id=(i%7)+1))
    people += [Person(101,"Manager Alpha",employment_type="MANAGER",manager=True,qualifications=frozenset({"SUPERVISOR"}),pattern=(0,1,2,3,4)),Person(102,"Manager Beta",employment_type="MANAGER",manager=True,qualifications=frozenset({"SUPERVISOR"}),pattern=(2,3,4,5,6))]
    # PT availability and assignment remain distinct: these one-day patterns are explicit accepted assignments.
    for d in range(7): people.append(Person(201+d,f"Part-time {d+1:02d}",employment_type="PART_TIME",supervisor=d%2==0,qualifications=frozenset({"PATROLLER","FIRST_TRACKS","NIGHT_SKI","SUPERVISOR"} if d%2==0 else {"PATROLLER","FIRST_TRACKS","NIGHT_SKI"}),pattern=(d,),available_dates=frozenset({week_start.fromordinal(week_start.toordinal()+d)}),history={}))
    rules=Rules(stations=(StationRule("DERCUM",1),StationRule("NORTH_PEAK",3,{"SUPERVISOR":1}),StationRule("OUTBACK",3,{"SUPERVISOR":1}),StationRule("BERGMAN",3,{"SUPERVISOR":1})),specialty_shifts=(ShiftRule("FIRST_TRACKS",2,1,"FIRST_TRACKS"),ShiftRule("NIGHT_SKI",2,1,"NIGHT_SKI")),budget_hours=1290)
    return Problem(week_start,people,rules)
