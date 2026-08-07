from __future__ import annotations

from datetime import date, timedelta
from time import monotonic

from ortools.sat.python import cp_model

from .models import (
    DailyAssignment,
    Employee,
    EmployeeSeasonStats,
    LockedAssignment,
    RookieStatus,
    ScheduleResult,
    SolverConfig,
)


class WeeklyDeploymentSolver:
    """CP-SAT model whose operational rules are supplied entirely by configuration."""

    def solve(
        self,
        week_start: date,
        employees: list[Employee],
        patterns: dict[str, tuple[int, ...]],
        config: SolverConfig,
        history: dict[str, EmployeeSeasonStats] | None = None,
        locks: tuple[LockedAssignment, ...] = (),
    ) -> ScheduleResult:
        started = monotonic()
        history = history or {}
        preflight = self._preflight(week_start, employees, patterns, config, locks)
        if preflight:
            return ScheduleResult(
                "INFEASIBLE",
                conflicts=preflight,
                solve_time_seconds=monotonic() - started,
            )

        model = cp_model.CpModel()
        employee_by_id = {e.id: e for e in employees if e.active}
        days = [week_start + timedelta(days=i) for i in range(7)]
        stations = [
            requirement.station_id for requirement in config.station_requirements
        ]
        shifts = [shift.id for shift in config.shift_types]
        shift_by_id = {shift.id: shift for shift in config.shift_types}
        normal_shift = next(
            (s.id for s in config.shift_types if s.kind.value == "STANDARD"), None
        )
        if normal_shift is None:
            return ScheduleResult(
                "INFEASIBLE",
                conflicts=[
                    self._conflict("CONFIGURATION", "No STANDARD shift is configured")
                ],
            )

        working: dict[tuple[str, int], bool] = {}
        station_vars = {}
        shift_vars = {}
        for employee in employee_by_id.values():
            workdays = set(patterns[employee.id])
            for day_index in range(7):
                working[employee.id, day_index] = day_index in workdays
                if day_index not in workdays:
                    continue
                for station in stations:
                    station_vars[employee.id, day_index, station] = model.new_bool_var(
                        f"station_{employee.id}_{day_index}_{station}"
                    )
                model.add_exactly_one(
                    station_vars[employee.id, day_index, station]
                    for station in stations
                )
                for shift in shifts:
                    shift_vars[employee.id, day_index, shift] = model.new_bool_var(
                        f"shift_{employee.id}_{day_index}_{shift}"
                    )
                model.add_exactly_one(
                    shift_vars[employee.id, day_index, shift] for shift in shifts
                )

                if employee.manager:
                    model.add(
                        station_vars[employee.id, day_index, config.manager_station_id]
                        == 1
                    )
                if employee.rookie_status == RookieStatus.ROOKIE:
                    model.add(
                        station_vars[employee.id, day_index, config.rookie_station_id]
                        == 1
                    )

            if (
                employee.rookie_status == RookieStatus.GRADUATED
                and not employee.manager
            ):
                for station in stations:
                    model.add(
                        sum(station_vars[employee.id, d, station] for d in workdays)
                        <= config.max_same_station_per_week
                    )

        for day_index in range(7):
            for requirement in config.station_requirements:
                present = [
                    station_vars[e.id, day_index, requirement.station_id]
                    for e in employee_by_id.values()
                    if working[e.id, day_index]
                ]
                model.add(sum(present) >= requirement.minimum_staff)
                supervisors = [
                    station_vars[e.id, day_index, requirement.station_id]
                    for e in employee_by_id.values()
                    if working[e.id, day_index] and e.supervisor
                ]
                model.add(sum(supervisors) >= requirement.supervisor_count)
                for (
                    qualification,
                    minimum,
                ) in requirement.qualification_minimums.items():
                    qualified = [
                        station_vars[e.id, day_index, requirement.station_id]
                        for e in employee_by_id.values()
                        if working[e.id, day_index]
                        and qualification in e.qualifications
                    ]
                    model.add(sum(qualified) >= minimum)

            specialty_supervisors: dict[str, list] = {}
            specialty_ids = set()
            for requirement in config.specialty_shift_requirements:
                if day_index not in requirement.active_weekdays:
                    continue
                specialty_ids.add(requirement.shift_type_id)
                assigned = [
                    shift_vars[e.id, day_index, requirement.shift_type_id]
                    for e in employee_by_id.values()
                    if working[e.id, day_index]
                ]
                model.add(sum(assigned) == requirement.count)
                supervisors = [
                    shift_vars[e.id, day_index, requirement.shift_type_id]
                    for e in employee_by_id.values()
                    if working[e.id, day_index] and e.supervisor
                ]
                specialty_supervisors[requirement.shift_type_id] = supervisors
                model.add(sum(supervisors) == requirement.supervisor_count)
                for employee in employee_by_id.values():
                    if not working[employee.id, day_index]:
                        continue
                    eligible = (
                        employee.first_tracks_eligible
                        if shift_by_id[requirement.shift_type_id].kind.value
                        == "FIRST_TRACKS"
                        else employee.night_ski_eligible
                    )
                    if not eligible:
                        model.add(
                            shift_vars[
                                employee.id, day_index, requirement.shift_type_id
                            ]
                            == 0
                        )
            for employee in employee_by_id.values():
                if working[employee.id, day_index] and specialty_ids:
                    model.add(
                        shift_vars[employee.id, day_index, normal_shift]
                        + sum(
                            shift_vars[employee.id, day_index, s] for s in specialty_ids
                        )
                        == 1
                    )

        # Different people necessarily supervise distinct specialty shifts because each employee has one shift.
        for lock in locks:
            day_index = (lock.day - week_start).days
            if lock.station_id:
                model.add(
                    station_vars[lock.employee_id, day_index, lock.station_id] == 1
                )
            if lock.shift_type_id:
                model.add(
                    shift_vars[lock.employee_id, day_index, lock.shift_type_id] == 1
                )

        objective_terms = []
        for employee in employee_by_id.values():
            stats = history.get(employee.id, EmployeeSeasonStats(employee.id))
            if (
                employee.rookie_status == RookieStatus.GRADUATED
                and not employee.manager
            ):
                for requirement in config.station_requirements:
                    prior = getattr(
                        stats, self._history_field(requirement.station_id), 0
                    )
                    objective_terms.extend(
                        config.fairness_weight
                        * prior
                        * station_vars[employee.id, d, requirement.station_id]
                        for d in patterns[employee.id]
                    )
        model.minimize(sum(objective_terms))
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = config.solver_time_limit_seconds
        status = solver.solve(model)
        elapsed = monotonic() - started
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return ScheduleResult(
                "INFEASIBLE",
                conflicts=[
                    self._conflict(
                        "CONSTRAINT_CONFLICT",
                        "No assignment satisfies all configured hard constraints",
                        [
                            "add qualified coverage",
                            "review locks",
                            "modify requirements explicitly",
                        ],
                    )
                ],
                solve_time_seconds=elapsed,
            )

        locked_keys = {(lock.employee_id, lock.day) for lock in locks}
        assignments = []
        for employee in employee_by_id.values():
            for day_index in patterns[employee.id]:
                station = next(
                    s
                    for s in stations
                    if solver.value(station_vars[employee.id, day_index, s])
                )
                shift = next(
                    s
                    for s in shifts
                    if solver.value(shift_vars[employee.id, day_index, s])
                )
                assignments.append(
                    DailyAssignment(
                        employee.id,
                        days[day_index],
                        True,
                        shift,
                        station,
                        shift_by_id[shift].paid_hours,
                        (employee.id, days[day_index]) in locked_keys,
                    )
                )
        return ScheduleResult(
            "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE",
            assignments,
            objective_value=solver.objective_value,
            solve_time_seconds=elapsed,
        )

    def _preflight(self, week_start, employees, patterns, config, locks):
        conflicts = []
        employee_by_id = {e.id: e for e in employees if e.active}
        for employee in employee_by_id.values():
            if employee.id not in patterns:
                conflicts.append(
                    self._conflict(
                        "MISSING_WORK_PATTERN",
                        f"{employee.id} has no awarded work pattern",
                    )
                )
                continue
            expected = (
                config.manager_shifts_per_week
                if employee.manager
                else config.normal_shifts_per_week
            )
            actual = len(set(patterns[employee.id]))
            if actual != expected:
                conflicts.append(
                    self._conflict(
                        "INVALID_WORK_PATTERN",
                        f"{employee.id} has {actual} days; configured requirement is {expected}",
                    )
                )
            hours = sum(
                next(
                    s.paid_hours
                    for s in config.shift_types
                    if s.kind.value == "STANDARD"
                )
                for _ in set(patterns[employee.id])
            )
            if not employee.manager and hours > config.max_weekly_hours:
                conflicts.append(
                    self._conflict(
                        "OVERTIME",
                        f"{employee.id} would work {hours} hours (maximum {config.max_weekly_hours})",
                    )
                )
            unavailable = set(patterns[employee.id]) & employee.unavailable_weekdays
            if unavailable:
                conflicts.append(
                    self._conflict(
                        "UNAVAILABILITY",
                        f"{employee.id} is assigned on unavailable weekdays {sorted(unavailable)}",
                    )
                )
        total_hours = sum(
            len(set(patterns.get(e.id, ())))
            * next(
                s.paid_hours for s in config.shift_types if s.kind.value == "STANDARD"
            )
            for e in employee_by_id.values()
        )
        if (
            config.hard_budget_hours is not None
            and total_hours > config.hard_budget_hours
        ):
            conflicts.append(
                self._conflict(
                    "HARD_BUDGET",
                    f"Scheduled {total_hours} hours exceeds hard budget {config.hard_budget_hours}",
                )
            )
        for lock in locks:
            employee = employee_by_id.get(lock.employee_id)
            index = (lock.day - week_start).days
            if employee is None or index not in patterns.get(lock.employee_id, ()):
                conflicts.append(
                    self._conflict(
                        "INVALID_LOCK",
                        f"Lock for {lock.employee_id} on {lock.day} is not a working assignment",
                    )
                )
        return conflicts

    @staticmethod
    def _history_field(station_id: str) -> str:
        return {
            "DERCUM": "dercum_days",
            "NORTH_PEAK": "north_peak_days",
            "OUTBACK": "outback_days",
            "BERGMAN": "bergman_days",
        }.get(station_id, "southside_total")

    @staticmethod
    def _conflict(category, message, resolutions=None):
        return {
            "category": category,
            "message": message,
            "possible_resolutions": resolutions or [],
        }
