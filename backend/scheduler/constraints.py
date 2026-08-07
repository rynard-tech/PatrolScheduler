"""CP-SAT constraint builders driven entirely by stored requirement data."""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping, Sequence

from backend.models.operations import RequirementSet, RequirementStrength, SpecialRoleRequirement


@dataclass
class ConstraintVariables:
    """Variables supplied by the deployment model, indexed by stable IDs."""

    station: Mapping[tuple[str, date, str], Any]
    role: Mapping[tuple[str, date, str], Any]
    shift: Mapping[tuple[str, date, str], Any]
    working: Mapping[tuple[str, date], Any]


@dataclass
class ConstraintContext:
    model: Any
    employees: Sequence[str]
    days: Sequence[date]
    qualifications: Mapping[str, frozenset[str]]
    variables: ConstraintVariables
    manager_ids: frozenset[str] = frozenset()
    soft_penalties: list[tuple[Any, int, str]] = field(default_factory=list)


def _shortfall(context: ConstraintContext, terms: list[Any], count: int, strength: RequirementStrength,
               label: str, weight: int = 1) -> None:
    if strength == RequirementStrength.HARD:
        context.model.Add(sum(terms) >= count)
    else:
        deficit = context.model.NewIntVar(0, count, f"shortfall_{label}")
        context.model.Add(sum(terms) + deficit >= count)
        context.soft_penalties.append((deficit, weight, label))


def add_station_requirements(context: ConstraintContext, requirements: RequirementSet) -> None:
    """Add non-Dercum floors and qualification coverage, leaving surplus at Dercum."""
    for day in context.days:
        station_ids = [item.station for item in requirements.station_requirements]
        for employee in context.employees:
            # This equality is what makes Dercum a remainder, rather than another
            # independently staffed quota: every worker has exactly one station.
            context.model.Add(sum(context.variables.station[employee, day, station]
                                  for station in station_ids)
                              == context.variables.working[employee, day])
        for requirement in requirements.station_requirements:
            station_terms = [context.variables.station[e, day, requirement.station]
                             for e in context.employees]
            if requirement.station != requirements.remainder_station:
                context.model.Add(sum(station_terms) >= requirement.minimum_staff)
                if requirement.target_staff > requirement.minimum_staff:
                    _shortfall(context, station_terms, requirement.target_staff,
                               RequirementStrength.SOFT,
                               f"{requirement.station}_{day}_target")
            for qualification, count in requirement.qualification_counts.items():
                eligible = [context.variables.station[e, day, requirement.station]
                            for e in context.employees
                            if qualification in context.qualifications.get(e, frozenset())]
                strength = requirement.qualification_strengths.get(
                    qualification, RequirementStrength.HARD)
                _shortfall(context, eligible, count, strength,
                           f"{requirement.station}_{day}_{qualification}")


def add_special_role_requirements(context: ConstraintContext,
                                  requirements: Sequence[SpecialRoleRequirement]) -> None:
    """Apply arbitrary date-effective roles and their station/shift/eligibility rules."""
    for requirement in requirements:
        for day in filter(requirement.applies_on, context.days):
            eligible = [e for e in context.employees if not requirement.eligibility_qualification
                        or requirement.eligibility_qualification in context.qualifications.get(e, frozenset())]
            terms = [context.variables.role[e, day, requirement.role] for e in eligible]
            label = f"{requirement.id}_{day}"
            _shortfall(context, terms, requirement.required_count, requirement.strength,
                       label, requirement.priority_weight)
            # A required count describes role slots, not merely a lower bound.
            context.model.Add(sum(terms) <= requirement.required_count)
            for employee in context.employees:
                role_var = context.variables.role[employee, day, requirement.role]
                if employee not in eligible:
                    context.model.Add(role_var == 0)
                else:
                    context.model.Add(role_var <= context.variables.working[employee, day])
                    if requirement.required_station:
                        context.model.Add(role_var <= context.variables.station[
                            employee, day, requirement.required_station])
                    if requirement.required_shift_type:
                        context.model.Add(role_var <= context.variables.shift[
                            employee, day, requirement.required_shift_type])
                    cost = _selection_cost(employee, requirement, len(context.employees))
                    if cost:
                        context.soft_penalties.append((role_var, cost, f"{label}_selection"))


def _selection_cost(employee: str, requirement: SpecialRoleRequirement, roster_size: int) -> int:
    """Rank candidates without turning a configured identity into a constraint."""
    if employee in requirement.preferred_employee_ids:
        return requirement.preferred_employee_ids.index(employee)
    if employee in requirement.backup_employee_ids:
        return len(requirement.preferred_employee_ids) + requirement.backup_employee_ids.index(employee) + 1
    # Unlisted eligible people remain feasible, but follow all named backups.
    return len(requirement.preferred_employee_ids) + len(requirement.backup_employee_ids) + roster_size


def add_manager_station_rules(context: ConstraintContext, remainder_station: str) -> None:
    """Managers who work are assigned to the configured remainder station."""
    for employee in context.manager_ids:
        for day in context.days:
            context.model.Add(context.variables.station[employee, day, remainder_station]
                              == context.variables.working[employee, day])


def add_operational_constraints(context: ConstraintContext, requirements: RequirementSet) -> None:
    add_station_requirements(context, requirements)
    add_special_role_requirements(context, requirements.special_role_requirements)
    add_manager_station_rules(context, requirements.remainder_station)
