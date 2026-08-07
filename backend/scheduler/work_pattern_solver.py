"""CP-SAT work-pattern award stage."""
from ortools.sat.python import cp_model
from .types import Person, Rules

def solve(people:list[Person], candidates:dict[int,list[tuple[int,...]]], rules:Rules):
    model=cp_model.CpModel(); choices={}
    for p in people:
        patterns=candidates.get(p.id,[p.pattern]); choices[p.id]=[model.NewBoolVar(f"p_{p.id}_{i}") for i in range(len(patterns))]; model.AddExactlyOne(choices[p.id])
        expected=rules.manager_shifts if p.manager else rules.ft_shifts
        for i,pattern in enumerate(patterns):
            if len(pattern)!=expected: model.Add(choices[p.id][i]==0)
    model.Minimize(sum(i*v for pid,vs in choices.items() for i,v in enumerate(vs)))
    solver=cp_model.CpSolver(); status=solver.Solve(model)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE): return {"status":"INFEASIBLE","awards":{}}
    return {"status":"OPTIMAL","awards":{p.id:candidates.get(p.id,[p.pattern])[next(i for i,v in enumerate(choices[p.id]) if solver.Value(v))] for p in people}}
