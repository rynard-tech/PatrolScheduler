from __future__ import annotations
from collections import Counter, defaultdict
from time import perf_counter
from ortools.sat.python import cp_model
from .constraints import exact_staff, exactly_one_station, fixed_value, minimum_staff, weekly_station_diversity
from .conflict_analysis import preflight, solver_conflict
from .objectives import fairness_cost
from .types import Assignment, Problem, SolveResult

def solve(problem:Problem, time_limit:float=15) -> SolveResult:
    started=perf_counter(); conflicts=preflight(problem)
    if conflicts: return SolveResult("INFEASIBLE",conflicts=conflicts,metrics={"solve_seconds":round(perf_counter()-started,4)})
    model=cp_model.CpModel(); stations=[s.code for s in problem.rules.stations]
    workers={(p.id,d):p for p in problem.people for d in p.pattern if (p.id,d) not in problem.approved_absences}
    x={(pid,d,s):model.NewBoolVar(f"station_{pid}_{d}_{s}") for pid,d in workers for s in stations}
    shift_codes=[s.code for s in problem.rules.specialty_shifts]
    y={(pid,d,sh):model.NewBoolVar(f"shift_{pid}_{d}_{sh}") for pid,d in workers for sh in shift_codes}
    for (pid,d),p in workers.items():
        exactly_one_station(model,[x[pid,d,s] for s in stations])
        model.Add(sum(y[pid,d,sh] for sh in shift_codes)<=1)
        if p.manager or p.rookie:
            fixed_value(model,x[pid,d,"DERCUM"])
    for d in range(7):
        day=[(pid,p) for (pid,dd),p in workers.items() if dd==d]
        for rule in problem.rules.stations:
            minimum_staff(model,[x[pid,d,rule.code] for pid,_ in day],rule.minimum)
            for qualification,minimum in rule.qualification_minimums.items():
                minimum_staff(model,[x[pid,d,rule.code] for pid,p in day if qualification in p.qualifications],minimum)
        for rule in problem.rules.specialty_shifts:
            eligible=[pid for pid,p in day if rule.eligibility is None or rule.eligibility in p.qualifications]
            exact_staff(model,[y[pid,d,rule.code] for pid in eligible],rule.count)
            for pid,p in day:
                if pid not in eligible: model.Add(y[pid,d,rule.code]==0)
            exact_staff(model,[y[pid,d,rule.code] for pid,p in day if p.supervisor],rule.supervisor_count)
    for p in problem.people:
        if not p.manager and not p.rookie:
            for s in stations: weekly_station_diversity(model,[x[p.id,d,s] for d in p.pattern if (p.id,d) in workers],problem.rules.max_station_repeats)
    for lock in problem.locks:
        if (lock.employee_id,lock.day) not in workers:
            return SolveResult("INFEASIBLE",conflicts=[{"code":"LOCK_ON_NONWORKING_DAY","employee_id":lock.employee_id,"day":lock.day}])
        if lock.station: fixed_value(model,x[lock.employee_id,lock.day,lock.station])
        if lock.shift:
            if lock.shift=="STANDARD": model.Add(sum(y[lock.employee_id,lock.day,sh] for sh in shift_codes)==0)
            else: fixed_value(model,y[lock.employee_id,lock.day,lock.shift])
    model.Minimize(sum(fairness_cost(p,s)*x[pid,d,s] for (pid,d),p in workers.items() for s in stations))
    solver=cp_model.CpSolver(); solver.parameters.max_time_in_seconds=time_limit; solver.parameters.num_search_workers=1; solver.parameters.random_seed=0
    status=solver.Solve(model)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE): return SolveResult("INFEASIBLE",conflicts=solver_conflict(),metrics={"solve_seconds":round(perf_counter()-started,4)})
    assignments=[]
    for (pid,d),p in sorted(workers.items(),key=lambda v:(v[0][1],v[0][0])):
        station=next(s for s in stations if solver.Value(x[pid,d,s])); shift=next((sh for sh in shift_codes if solver.Value(y[pid,d,sh])),"STANDARD")
        role="MANAGER" if p.manager else ("SUPERVISOR" if p.supervisor else "PATROLLER")
        assignments.append(Assignment(pid,p.name,problem.week_start.fromordinal(problem.week_start.toordinal()+d),station,shift,problem.rules.hours_per_shift,role))
    totals=Counter((a.date.isoformat(),a.station) for a in assignments); shifts=Counter((a.date.isoformat(),a.shift_type) for a in assignments)
    actual=len(assignments)*problem.rules.hours_per_shift
    return SolveResult("OPTIMAL" if status==cp_model.OPTIMAL else "FEASIBLE",assignments,metrics={"solve_seconds":round(perf_counter()-started,4),"staffing_totals":{f"{d}:{s}":n for (d,s),n in totals.items()},"shift_totals":{f"{d}:{s}":n for (d,s),n in shifts.items()},"actual_hours":actual,"budget_hours":problem.rules.budget_hours,"budget_variance":None if problem.rules.budget_hours is None else problem.rules.budget_hours-actual})
