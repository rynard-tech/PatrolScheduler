from .types import Problem

def preflight(problem:Problem) -> list[dict]:
    conflicts=[]; rules=problem.rules
    work={(p.id,d) for p in problem.people for d in p.pattern}
    actual_hours=len(work)*rules.hours_per_shift
    if rules.budget_hard and rules.budget_hours is not None and actual_hours>rules.budget_hours:
        conflicts.append({"code":"HARD_BUDGET_CONFLICT","message":f"scheduled {actual_hours} hours exceeds hard budget {rules.budget_hours}","resolutions":["increase budget","reduce configured staffing"]})
    for p in problem.people:
        expected=rules.manager_shifts if p.manager else (rules.ft_shifts if p.employment_type=="FULL_TIME" else None)
        if expected is not None and len(p.pattern)!=expected: conflicts.append({"code":"OVERTIME_OR_PATTERN","employee_id":p.id,"message":f"configured pattern has {len(p.pattern)} shifts; expected {expected}"})
        for d in p.pattern:
            if (p.id,d) in problem.approved_absences: conflicts.append({"code":"APPROVED_ABSENCE_CONFLICT","employee_id":p.id,"day":d,"message":"work pattern conflicts with approved absence"})
    for d in range(7):
        workers=[p for p in problem.people if d in p.pattern and (p.id,d) not in problem.approved_absences]
        for sr in rules.stations:
            if len(workers)<sr.minimum: conflicts.append({"code":"STAFFING_SHORTAGE","day":d,"station":sr.code,"required":sr.minimum})
            for q,n in sr.qualification_minimums.items():
                if sum(q in p.qualifications for p in workers)<n: conflicts.append({"code":"QUALIFICATION_SHORTAGE","day":d,"station":sr.code,"qualification":q,"required":n})
        for sh in rules.specialty_shifts:
            eligible=[p for p in workers if sh.eligibility is None or sh.eligibility in p.qualifications]
            if len(eligible)<sh.count: conflicts.append({"code":"SHIFT_QUALIFICATION_SHORTAGE","day":d,"shift":sh.code,"required":sh.count})
            if sum(p.supervisor for p in eligible)<sh.supervisor_count: conflicts.append({"code":"SUPERVISOR_SHORTAGE","day":d,"shift":sh.code,"required":sh.supervisor_count})
    seen={}
    for lock in problem.locks:
        key=(lock.employee_id,lock.day)
        prior=seen.get(key)
        if prior and ((prior.station and lock.station and prior.station!=lock.station) or (prior.shift and lock.shift and prior.shift!=lock.shift)):
            conflicts.append({"code":"CONFLICTING_LOCKS","employee_id":lock.employee_id,"day":lock.day,"message":"locks demand incompatible values"})
        seen[key]=lock
    return conflicts

def solver_conflict() -> list[dict]:
    return [{"code":"CONSTRAINT_SYSTEM_INFEASIBLE","message":"CP-SAT proved that staffing, qualification, diversity, shift, or lock constraints conflict","resolutions":["add qualified part-time coverage","change a work pattern","remove or override a lock","modify a hard requirement"]}]
