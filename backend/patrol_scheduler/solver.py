"""CP-SAT week-pattern and staffing-wave solver with explicit validation."""
from __future__ import annotations
from collections import Counter
import importlib.util
if importlib.util.find_spec("ortools") is not None:
    from ortools.sat.python import cp_model
else:
    cp_model = None
from .models import *


def solve_week(data: ScheduleInput) -> SolveResult:
    if cp_model is None:
        return _solve_without_ortools(data)
    model = cp_model.CpModel()
    patterns = {p.id: p for p in data.patterns}
    normal = [e for e in data.employees if e.normal_full_time]
    managers = [e for e in data.employees if e.manager]
    explicit = [e for e in data.employees if e.explicit_paid_weekdays]
    eligible: dict[str, list[str]] = {}
    choose = {}
    active = {}
    conflicts: list[str] = []

    for e in normal:
        ids = [r.pattern_id for r in e.ranked_patterns if r.pattern_id in patterns]
        if not ids:
            conflicts.append(f"{e.id} has no valid ranked work pattern")
            continue
        eligible[e.id] = ids
        active[e.id] = model.NewBoolVar(f"active_{e.id}")
        for pid in ids:
            choose[e.id, pid] = model.NewBoolVar(f"pattern_{e.id}_{pid}")
        model.Add(sum(choose[e.id, pid] for pid in ids) == active[e.id])

    if conflicts:
        return SolveResult("INFEASIBLE", conflicts=conflicts, validation={"valid": False})

    wave = next((w for w in data.waves if w.id == data.selected_wave_id), None)
    if wave:
        required_normal = wave.active_employee_count - len(managers) - len(explicit)
        if required_normal < 0 or required_normal > len(normal):
            return SolveResult("INFEASIBLE", conflicts=["selected wave active count is incompatible with roster"], validation={"valid": False})
        model.Add(sum(active.values()) == required_normal)
    else:
        for var in active.values(): model.Add(var == 1)

    # Managers and explicit paid statuses have their own calendars, never FT pattern math.
    manager_days = {e.id: set(WEEKDAYS[:5]) for e in managers}
    explicit_days = {e.id: set(e.explicit_paid_weekdays) for e in explicit}
    def work_expr(e: Employee, day: str):
        if e.normal_full_time:
            return sum(choose[e.id, pid] for pid in eligible[e.id] if day in patterns[pid].weekdays)
        return int(day in manager_days.get(e.id, explicit_days.get(e.id, set())))

    if data.operating_period.max_budgeted_hours is not None:
        total = sum(data.shift_hours * work_expr(e, day) for e in data.employees for day in WEEKDAYS)
        model.Add(total <= data.operating_period.max_budgeted_hours)

    # Qualification counts are hard operational rules; ordinary headcount becomes a reported shortage.
    for req in data.operating_period.requirements:
        if req.qualification and req.qualified_count:
            qualified = [e for e in data.employees if req.qualification in e.qualifications]
            if not qualified:
                return SolveResult("INFEASIBLE", conflicts=[f"{req.weekday}: no employee has qualification {req.qualification}"], validation={"valid": False})
            model.Add(sum(work_expr(e, req.weekday) for e in qualified) >= req.qualified_count)

    # Lexicographic-style scaling: coverage balance dominates ranked preference; seniority breaks ties.
    deviations = []
    target = round((wave.target_people_per_day if wave else sum(r.minimum_staff for r in data.operating_period.requirements)/7))
    for day in WEEKDAYS:
        count = sum(work_expr(e, day) for e in data.employees)
        dev = model.NewIntVar(0, len(data.employees), f"deviation_{day}")
        model.AddAbsEquality(dev, count - target)
        deviations.append(dev)
    preference_cost = []
    seniority_order = {e.id: rank for rank, e in enumerate(sorted(normal, key=lambda x: (-x.prior_winter_hours, x.id)))}
    for e in normal:
        ranks = {r.pattern_id: r.rank for r in e.ranked_patterns}
        # Larger seniority multiplier makes the same preference gain go to the senior employee.
        weight = len(normal) - seniority_order[e.id]
        for pid in eligible[e.id]:
            preference_cost.append((ranks[pid]-1) * weight * choose[e.id, pid])
    model.Minimize(10000 * sum(deviations) + sum(preference_cost))
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        reasons = ["hard budget, active-wave, pattern, or qualification constraints contradict"]
        return SolveResult("INFEASIBLE", conflicts=reasons, validation={"valid": False})

    awarded = {e.id: next(pid for pid in eligible[e.id] if solver.Value(choose[e.id, pid]))
               for e in normal if solver.Value(active[e.id])}
    assignments: list[Assignment] = []
    for e in data.employees:
        days = set(patterns[awarded[e.id]].weekdays) if e.id in awarded else manager_days.get(e.id, explicit_days.get(e.id, set()))
        for day in WEEKDAYS:
            worked = day in days
            assignments.append(Assignment(e.id, day, worked, data.shift_hours if worked else 0,
                                          "EXPLICIT_PAID" if e.explicit_paid_weekdays and worked else "WORKED"))
    counts = Counter(a.weekday for a in assignments if a.worked)
    shortages = [{"weekday": r.weekday, "required": r.minimum_staff, "scheduled": counts[r.weekday],
                  "shortage": r.minimum_staff-counts[r.weekday]}
                 for r in data.operating_period.requirements if counts[r.weekday] < r.minimum_staff]
    validation = validate(data, assignments, awarded)
    result_status = "VALID_WITH_SHORTAGES" if shortages else "VALID"
    return SolveResult(result_status, assignments, awarded, sorted(awarded), shortages, validation=validation)


def validate(data: ScheduleInput, assignments: list[Assignment], awarded: dict[str, str]) -> dict:
    errors = []
    by_employee = {e.id: [a for a in assignments if a.employee_id == e.id and a.worked] for e in data.employees}
    for e in data.employees:
        if e.normal_full_time and e.id in awarded:
            hours = sum(a.paid_hours for a in by_employee[e.id])
            if len(by_employee[e.id]) != 4 or hours != 40:
                errors.append(f"{e.id}: normal FT must have four shifts and 40 hours")
    return {"valid": not errors, "errors": errors}


def _solve_without_ortools(data: ScheduleInput) -> SolveResult:
    """Deterministic dependency fallback; production installs use CP-SAT above."""
    patterns = {p.id: p for p in data.patterns}
    normal = [e for e in data.employees if e.normal_full_time]
    managers = [e for e in data.employees if e.manager]
    explicit = [e for e in data.employees if e.explicit_paid_weekdays]
    wave = next((w for w in data.waves if w.id == data.selected_wave_id), None)
    active_count = (wave.active_employee_count - len(managers) - len(explicit)) if wave else len(normal)
    if active_count < 0 or active_count > len(normal):
        return SolveResult("INFEASIBLE", conflicts=["selected wave active count is incompatible with roster"], validation={"valid": False})
    active = sorted(normal, key=lambda e: (-e.prior_winter_hours, e.id))[:active_count]
    eligible = {e.id: [r.pattern_id for r in e.ranked_patterns if r.pattern_id in patterns] for e in active}
    missing = [e.id for e in active if not eligible[e.id]]
    if missing:
        return SolveResult("INFEASIBLE", conflicts=[f"{missing[0]} has no valid ranked work pattern"], validation={"valid": False})
    fixed_days = {e.id: set(WEEKDAYS[:5]) for e in managers}
    fixed_days.update({e.id: set(e.explicit_paid_weekdays) for e in explicit})
    total_hours = data.shift_hours * (4 * len(active) + sum(len(v) for v in fixed_days.values()))
    if data.operating_period.max_budgeted_hours is not None and total_hours > data.operating_period.max_budgeted_hours:
        return SolveResult("INFEASIBLE", conflicts=["hard budget, active-wave, pattern, or qualification constraints contradict"], validation={"valid": False})
    for req in data.operating_period.requirements:
        if req.qualification and req.qualified_count:
            qualified = [e for e in [*active, *managers, *explicit] if req.qualification in e.qualifications]
            if len(qualified) < req.qualified_count:
                return SolveResult("INFEASIBLE", conflicts=[f"{req.weekday}: no employee has qualification {req.qualification}"], validation={"valid": False})
    awarded = {e.id: eligible[e.id][0] for e in active}
    target = round(wave.target_people_per_day if wave else 0)
    seniority = {e.id: len(active)-i for i,e in enumerate(active)}
    ranks = {e.id: {r.pattern_id:r.rank for r in e.ranked_patterns} for e in active}
    def cost(candidate):
        coverage = {d: sum(d in fixed for fixed in fixed_days.values()) for d in WEEKDAYS}
        for eid,pid in candidate.items():
            for d in patterns[pid].weekdays: coverage[d] += 1
        return 10000*sum(abs(coverage[d]-target) for d in WEEKDAYS) + sum((ranks[e.id][candidate[e.id]]-1)*seniority[e.id] for e in active)
    # Coordinate descent is sufficient as a portable demonstration; CP-SAT remains authoritative.
    changed = True
    while changed:
        changed = False
        base = cost(awarded)
        best = (base, None, None)
        for e in active:
            for pid in eligible[e.id]:
                trial = dict(awarded); trial[e.id] = pid
                proposal = (cost(trial), e.id, pid)
                if proposal[0] < best[0] or (proposal[0] == best[0] and best[1] is not None and proposal[1:] < best[1:]): best = proposal
        if best[0] < base:
            awarded[best[1]] = best[2]; changed = True
    assignments = []
    for e in data.employees:
        days = set(patterns[awarded[e.id]].weekdays) if e.id in awarded else fixed_days.get(e.id, set())
        for day in WEEKDAYS:
            worked = day in days
            assignments.append(Assignment(e.id, day, worked, data.shift_hours if worked else 0,
                                          "EXPLICIT_PAID" if e.explicit_paid_weekdays and worked else "WORKED"))
    counts = Counter(a.weekday for a in assignments if a.worked)
    shortages = [{"weekday":r.weekday,"required":r.minimum_staff,"scheduled":counts[r.weekday],"shortage":r.minimum_staff-counts[r.weekday]}
                 for r in data.operating_period.requirements if counts[r.weekday] < r.minimum_staff]
    validation = validate(data, assignments, awarded)
    return SolveResult("VALID_WITH_SHORTAGES" if shortages else "VALID", assignments, awarded,
                       sorted(awarded), shortages, validation=validation)
