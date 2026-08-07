"""CP-SAT roster selection stage honoring capacity and qualification minima."""
from ortools.sat.python import cp_model

def solve(people, capacity:int, qualification_minimums:dict[str,int]):
    model=cp_model.CpModel(); active={p.id:model.NewBoolVar(f"active_{p.id}") for p in people}; model.Add(sum(active.values())<=capacity)
    for q,n in qualification_minimums.items(): model.Add(sum(active[p.id] for p in people if q in p.qualifications)>=n)
    model.Maximize(sum((len(people)-i)*active[p.id] for i,p in enumerate(people)))
    solver=cp_model.CpSolver(); status=solver.Solve(model)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE): return {"status":"INFEASIBLE","active_employee_ids":[]}
    return {"status":"OPTIMAL","active_employee_ids":[p.id for p in people if solver.Value(active[p.id])]}
