from dataclasses import replace
from backend.fixtures import synthetic_problem
from backend.scheduler.deployment_solver import solve
from backend.scheduler.types import Lock, Person, StationRule
from backend.scheduler.validation import validate

def test_feasible_complete_week_and_all_hard_rules():
    p=synthetic_problem(); result=solve(p)
    assert result.status=="OPTIMAL"; check=validate(p,result); assert check=={"valid":True,"violations":[]}
    assert {a.shift_type for a in result.assignments}>={"STANDARD","FIRST_TRACKS","NIGHT_SKI"}

def test_qualification_shortage_is_explicit():
    p=synthetic_problem(); p.people=[replace(x,qualifications=x.qualifications-{"SUPERVISOR"}) for x in p.people]
    r=solve(p); assert r.status=="INFEASIBLE"; assert "QUALIFICATION_SHORTAGE" in {x["code"] for x in r.conflicts}

def test_supervisor_shortage_is_explicit():
    p=synthetic_problem(); p.people=[replace(x,supervisor=False) for x in p.people]
    r=solve(p); assert "SUPERVISOR_SHORTAGE" in {x["code"] for x in r.conflicts}

def test_overtime_pattern_is_rejected():
    p=synthetic_problem(); p.people[0]=replace(p.people[0],pattern=(0,1,2,3,4))
    assert "OVERTIME_OR_PATTERN" in {x["code"] for x in solve(p).conflicts}

def test_conflicting_locks_are_reported():
    p=synthetic_problem(); p.locks=[Lock(1,0,station="DERCUM"),Lock(1,0,station="BERGMAN")]
    assert "CONFLICTING_LOCKS" in {x["code"] for x in solve(p).conflicts}

def test_approved_absence_is_not_silently_scheduled():
    p=synthetic_problem(); p.approved_absences.add((1,0))
    assert "APPROVED_ABSENCE_CONFLICT" in {x["code"] for x in solve(p).conflicts}

def test_station_diversity_lock_conflict_is_infeasible():
    p=synthetic_problem(); person=p.people[0]; p.locks=[Lock(person.id,d,station="BERGMAN") for d in person.pattern[:3]]
    assert solve(p).status=="INFEASIBLE"

def test_hard_budget_conflict_is_explicit():
    p=synthetic_problem(); p.rules=replace(p.rules,budget_hours=100)
    assert "HARD_BUDGET_CONFLICT" in {x["code"] for x in solve(p).conflicts}
