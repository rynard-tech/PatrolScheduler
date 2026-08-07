from __future__ import annotations

from time import monotonic

from ortools.sat.python import cp_model

from .conflicts import analyze_conflicts
from .models import (
    DEFAULT_SHIFTS,
    AssignmentLock,
    DailyAssignment,
    RookieStatus,
    RuleStrength,
    Shift,
    SolveResult,
    Station,
    WeeklyInput,
)


class DeploymentSolver:
    """CP-SAT weekly station/shift/role assignment with staged objectives."""

    def solve(self, data: WeeklyInput) -> SolveResult:
        started = monotonic()
        model = cp_model.CpModel()
        employees = {
            employee.id: employee for employee in data.employees if employee.active
        }
        days = sorted(data.requirements_by_date)
        scheduled = {
            (employee_id, day)
            for employee_id, workdays in data.workdays.items()
            for day in workdays
            if employee_id in employees
            and day in data.requirements_by_date
            and day not in data.unavailable.get(employee_id, set())
            and day not in data.approved_pto.get(employee_id, set())
        }

        station_vars = {}
        shift_vars = {}
        role_vars = {}
        requirements_by_station = {}
        locks = {(lock.employee_id, lock.day): lock for lock in data.locks}

        for employee_id, day in sorted(scheduled):
            employee = employees[employee_id]
            station_options = [
                station
                for station in Station
                if self._station_allowed(employee, station)
            ]
            shift_options = [
                shift for shift in Shift if self._shift_allowed(employee, shift)
            ]
            for station in station_options:
                station_vars[employee_id, day, station] = model.new_bool_var(
                    f"station_{employee_id}_{day}_{station}"
                )
            for shift in shift_options:
                shift_vars[employee_id, day, shift] = model.new_bool_var(
                    f"shift_{employee_id}_{day}_{shift}"
                )
            model.add_exactly_one(
                station_vars[employee_id, day, station] for station in station_options
            )
            model.add_exactly_one(
                shift_vars[employee_id, day, shift] for shift in shift_options
            )

            requirement_set = data.requirements_by_date[day]
            for station_requirement in requirement_set.station_requirements:
                requirements_by_station[day, station_requirement.station] = (
                    station_requirement
                )
                for role in station_requirement.roles:
                    if (
                        role.qualification in employee.qualifications
                        and (employee_id, day, station_requirement.station)
                        in station_vars
                    ):
                        var = model.new_bool_var(
                            f"role_{employee_id}_{day}_{station_requirement.station}_{role.role}"
                        )
                        role_vars[
                            employee_id, day, station_requirement.station, role.role
                        ] = var
                        model.add(
                            var
                            <= station_vars[
                                employee_id, day, station_requirement.station
                            ]
                        )
            employee_roles = [
                var
                for key, var in role_vars.items()
                if key[0] == employee_id and key[1] == day
            ]
            if employee_roles:
                model.add_at_most_one(employee_roles)
            self._apply_lock(
                model,
                locks.get((employee_id, day)),
                station_vars,
                shift_vars,
                role_vars,
            )

        for day in days:
            requirement_set = data.requirements_by_date[day]
            daily = [(employee_id, d) for employee_id, d in scheduled if d == day]
            if requirement_set.max_paid_hours is not None:
                model.add(len(daily) * 10 <= requirement_set.max_paid_hours)
            for station_requirement in requirement_set.station_requirements:
                station_staff = [
                    station_vars[key]
                    for key in station_vars
                    if key[1:] == (day, station_requirement.station)
                ]
                model.add(sum(station_staff) >= station_requirement.minimum)
                for role in station_requirement.roles:
                    eligible_roles = [
                        var
                        for key, var in role_vars.items()
                        if key[1:] == (day, station_requirement.station, role.role)
                    ]
                    model.add(sum(eligible_roles) >= role.count)
            for shift_requirement in requirement_set.shift_requirements:
                shift_staff = [
                    shift_vars[key]
                    for key in shift_vars
                    if key[1:] == (day, shift_requirement.shift)
                ]
                shift_supervisors = [
                    var
                    for key, var in shift_vars.items()
                    if key[1:] == (day, shift_requirement.shift)
                    and employees[key[0]].supervisor
                ]
                model.add(sum(shift_staff) == shift_requirement.count)
                model.add(sum(shift_supervisors) == shift_requirement.supervisor_count)

            # The supervisors of the two specialty shifts must be different. Since
            # each employee receives exactly one shift, this is enforced naturally.

        if data.config.station_repeat_rule == RuleStrength.HARD:
            for employee_id, employee in employees.items():
                exempt = (
                    employee.manager
                    or employee.rookie_status == RookieStatus.ROOKIE
                    or employee.required_station is not None
                    or employee_id in data.repeat_overrides
                )
                if not exempt:
                    for station in Station:
                        model.add(
                            sum(
                                var
                                for key, var in station_vars.items()
                                if key[0] == employee_id and key[2] == station
                            )
                            <= data.config.station_max_repeats
                        )

        # Stage B: minimize deviation above station targets. Minimum staffing is hard.
        over_target = []
        for (day, station), requirement in requirements_by_station.items():
            count = sum(
                var for key, var in station_vars.items() if key[1:] == (day, station)
            )
            excess = model.new_int_var(0, len(employees), f"excess_{day}_{station}")
            model.add(excess >= count - requirement.target)
            over_target.append(excess)
        operational = sum(over_target)
        stage_values: dict[str, int] = {}
        solver = self._solver(data)
        model.minimize(operational)
        status = solver.solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return SolveResult(
                "INFEASIBLE",
                conflicts=analyze_conflicts(data),
                solve_time_seconds=monotonic() - started,
            )
        operational_value = int(solver.value(operational))
        stage_values["operational_overstaffing"] = operational_value
        model.add(operational == operational_value)

        # Stage D/E: among operationally equivalent schedules, balance historical
        # station exposure and reward under-served family/manager relationships.
        fairness_terms = []
        relationship_terms = []
        managers = [employee for employee in employees.values() if employee.manager]
        for key, var in station_vars.items():
            employee_id, day, station = key
            fairness_terms.append(
                data.station_history.get(employee_id, {}).get(station, 0) * var
            )
            employee = employees[employee_id]
            if employee.family_supervisor_id:
                supervisor_id = employee.family_supervisor_id
                supervisor_var = station_vars.get((supervisor_id, day, station))
                if supervisor_var is not None:
                    overlap = model.new_bool_var(
                        f"family_overlap_{employee_id}_{supervisor_id}_{day}_{station}"
                    )
                    model.add(overlap <= var)
                    model.add(overlap <= supervisor_var)
                    model.add(overlap >= var + supervisor_var - 1)
                    prior = data.family_exposure.get((supervisor_id, employee_id), 0)
                    relationship_terms.append((20 - min(prior, 20)) * overlap)
            if employee.supervisor and station == Station.DERCUM:
                for manager in managers:
                    manager_var = station_vars.get((manager.id, day, Station.DERCUM))
                    if manager_var is not None:
                        overlap = model.new_bool_var(
                            f"manager_overlap_{manager.id}_{employee_id}_{day}"
                        )
                        model.add(overlap <= var)
                        model.add(overlap <= manager_var)
                        model.add(overlap >= var + manager_var - 1)
                        prior = data.manager_supervisor_exposure.get(
                            (manager.id, employee_id), 0
                        )
                        relationship_terms.append((20 - min(prior, 20)) * overlap)
        fairness_cost = sum(fairness_terms) - sum(relationship_terms)
        model.minimize(fairness_cost)
        status = solver.solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return SolveResult(
                "INFEASIBLE",
                conflicts=analyze_conflicts(data),
                solve_time_seconds=monotonic() - started,
            )
        stage_values["fairness_relationship_cost"] = int(solver.value(fairness_cost))

        assignments = []
        for employee_id, day in sorted(scheduled, key=lambda item: (item[1], item[0])):
            employee = employees[employee_id]
            station = next(
                station
                for station in Station
                if (var := station_vars.get((employee_id, day, station))) is not None
                and solver.boolean_value(var)
            )
            shift = next(
                shift
                for shift in Shift
                if (var := shift_vars.get((employee_id, day, shift))) is not None
                and solver.boolean_value(var)
            )
            roles = [
                key[3]
                for key, var in role_vars.items()
                if key[:3] == (employee_id, day, station) and solver.boolean_value(var)
            ]
            definition = DEFAULT_SHIFTS[shift]
            assignments.append(
                DailyAssignment(
                    employee_id,
                    employee.display_name,
                    day,
                    shift,
                    station,
                    roles[0] if roles else "PATROLLER",
                    definition.start,
                    definition.end,
                    definition.paid_hours,
                    (employee_id, day) in locks,
                )
            )
        return SolveResult(
            "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE",
            assignments,
            solve_time_seconds=monotonic() - started,
            objective_values=stage_values,
        )

    @staticmethod
    def _solver(data: WeeklyInput) -> cp_model.CpSolver:
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = data.config.time_limit_seconds
        solver.parameters.random_seed = data.config.random_seed
        solver.parameters.num_search_workers = 1
        return solver

    @staticmethod
    def _station_allowed(employee, station: Station) -> bool:
        if employee.manager or employee.rookie_status == RookieStatus.ROOKIE:
            return station == Station.DERCUM
        if employee.required_station:
            return station == employee.required_station
        return station not in employee.prohibited_stations and (
            not employee.allowed_stations or station in employee.allowed_stations
        )

    @staticmethod
    def _shift_allowed(employee, shift: Shift) -> bool:
        if shift == Shift.NIGHT_SKI:
            return employee.night_ski_eligible
        if shift == Shift.FIRST_TRACKS:
            return employee.first_tracks_eligible
        return True

    @staticmethod
    def _apply_lock(
        model, lock: AssignmentLock | None, stations, shifts, roles
    ) -> None:
        if not lock:
            return
        key_prefix = (lock.employee_id, lock.day)
        if lock.station is not None:
            variable = stations.get((*key_prefix, lock.station))
            model.add(variable == 1) if variable is not None else model.add_bool_or([])
        if lock.shift is not None:
            variable = shifts.get((*key_prefix, lock.shift))
            model.add(variable == 1) if variable is not None else model.add_bool_or([])
        if lock.role is not None:
            matching = [
                var
                for key, var in roles.items()
                if key[:2] == key_prefix and key[3] == lock.role
            ]
            model.add(sum(matching) == 1)
