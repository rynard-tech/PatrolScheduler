"""Independent checks over emitted assignments; does not trust the solver."""
from collections import Counter, defaultdict
from .types import Problem, SolveResult

def validate(problem:Problem, result:SolveResult) -> dict:
    violations=[]
    if result.status not in {"OPTIMAL","FEASIBLE"}: return {"valid":False,"violations":[{"code":"NO_SCHEDULE"}]}
    by_employee=defaultdict(list); by_day=defaultdict(list)
    people={p.id:p for p in problem.people}
    for a in result.assignments: by_employee[a.employee_id].append(a); by_day[(a.date-problem.week_start).days].append(a)
    for p in problem.people:
        rows=by_employee[p.id]
        if p.employment_type=="FULL_TIME":
            expected=problem.rules.manager_shifts if p.manager else problem.rules.ft_shifts
            if len(rows)!=expected: violations.append({"code":"SHIFT_COUNT","employee_id":p.id,"actual":len(rows),"expected":expected})
            if not p.manager and sum(a.paid_hours for a in rows)>problem.rules.max_ft_hours: violations.append({"code":"OVERTIME","employee_id":p.id})
        counts=Counter(a.station for a in rows)
        if p.manager and any(a.station!="DERCUM" for a in rows): violations.append({"code":"MANAGER_STATION","employee_id":p.id})
        if p.rookie and any(a.station!="DERCUM" for a in rows): violations.append({"code":"ROOKIE_STATION","employee_id":p.id})
        if not p.manager and not p.rookie and counts and max(counts.values())>problem.rules.max_station_repeats: violations.append({"code":"STATION_DIVERSITY","employee_id":p.id})
        if any((p.id,(a.date-problem.week_start).days) in problem.approved_absences for a in rows): violations.append({"code":"APPROVED_ABSENCE","employee_id":p.id})
    for d,rows in by_day.items():
        for rule in problem.rules.stations:
            stationed=[a for a in rows if a.station==rule.code]
            if len(stationed)<rule.minimum: violations.append({"code":"STATION_MINIMUM","day":d,"station":rule.code})
            for q,n in rule.qualification_minimums.items():
                if sum(q in people[a.employee_id].qualifications for a in stationed)<n: violations.append({"code":"QUALIFICATION_MINIMUM","day":d,"station":rule.code,"qualification":q})
        supervisors={}
        for rule in problem.rules.specialty_shifts:
            shifted=[a for a in rows if a.shift_type==rule.code]
            if len(shifted)!=rule.count: violations.append({"code":"SHIFT_COUNT_DAILY","day":d,"shift":rule.code})
            supervisors[rule.code]={a.employee_id for a in shifted if people[a.employee_id].supervisor}
            if len(supervisors[rule.code])!=rule.supervisor_count: violations.append({"code":"SHIFT_SUPERVISOR_COUNT","day":d,"shift":rule.code})
        if len(supervisors)>=2 and set.intersection(*supervisors.values()): violations.append({"code":"SPECIALTY_SUPERVISOR_OVERLAP","day":d})
    hours=sum(a.paid_hours for a in result.assignments)
    if problem.rules.budget_hard and problem.rules.budget_hours is not None and hours>problem.rules.budget_hours: violations.append({"code":"HARD_BUDGET"})
    return {"valid":not violations,"violations":violations}
