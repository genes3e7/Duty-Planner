"""
app/core/scheduler.py

This module contains the core logic for the scheduling engine using OR-Tools.
It defines the solver model, variables, and constraints.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ortools.sat.python import cp_model

from app import constants as C
from app.models.config import AppConfig

logger = logging.getLogger(__name__)


class SolverRequest:
    """
    Data Transfer Object (DTO) containing all necessary data to run the solver.
    Decouples the UI data structures from the core logic.
    """

    def __init__(
        self,
        staff_ids: List[str],
        year: int,
        month: int,
        fixed_assignments: Dict[Tuple[str, int], str],
        day_modes: Dict[int, str],
        inactive_days: List[int],
        shift_weights: Dict[Tuple[int, str], int],
    ):
        self.staff_ids = staff_ids
        self.year = year
        self.month = month
        self.fixed_assignments = fixed_assignments
        self.day_modes = day_modes
        self.inactive_days = inactive_days
        self.shift_weights = shift_weights  # Mapping: (Day, Shift) -> Scaled Integer Points


class DutySchedulerEngine:
    """
    The main engine wrapping Google OR-Tools CP-SAT solver.
    """

    def __init__(self, config: AppConfig, prev_balance: Dict[str, float], request: SolverRequest):
        self.config = config
        self.prev_balance = prev_balance
        self.req = request
        self.model = cp_model.CpModel()
        self.vars: Dict[Tuple[str, int, str], Any] = {}
        self.shifts = list(C.ACTIVE_DUTIES)  # AM, PM, 24H, S/B
        self.soft_ban_penalties: List[Any] = []  # Stores penalty variables for soft bans

        # Determine number of days from the day_modes map
        self.days_range = sorted(self.req.day_modes.keys())

    def build_model(self):
        """
        Constructs the CP-SAT model: variables, hard constraints, and objective.
        """
        if not self.req.staff_ids:
            logger.warning("No staff IDs provided. Returning empty model.")
            return

        self._create_variables()
        self._apply_daily_coverage()
        self._apply_fixed_assignments()
        self._apply_shift_logic()
        self._apply_fairness_objective()

    def _create_variables(self):
        """Creates boolean variables for each person, day, and shift."""
        for person in self.req.staff_ids:
            for day in self.days_range:
                if day in self.req.inactive_days:
                    continue

                for shift in self.shifts:
                    self.vars[(person, day, shift)] = self.model.NewBoolVar(f"{person}_{day}_{shift}")

    def _apply_daily_coverage(self):
        """Ensures the required number of people are assigned to each shift type."""
        for day in self.days_range:
            if day in self.req.inactive_days:
                continue

            mode = self.req.day_modes.get(day, C.ScheduleMode.SHIFT.value)

            if mode == C.ScheduleMode.FULL_24H.value:
                needed_24h = self.config.constraints.personnel_needed_per_shift.get("24H", 1)
                self.model.Add(
                    sum(self.vars[(p, day, "24H")] for p in self.req.staff_ids if (p, day, "24H") in self.vars)
                    == needed_24h
                )

                for p in self.req.staff_ids:
                    if (p, day, "AM") in self.vars:
                        self.model.Add(self.vars[(p, day, "AM")] == 0)
                    if (p, day, "PM") in self.vars:
                        self.model.Add(self.vars[(p, day, "PM")] == 0)

            else:
                needed_am = self.config.constraints.personnel_needed_per_shift.get("AM", 1)
                needed_pm = self.config.constraints.personnel_needed_per_shift.get("PM", 1)

                self.model.Add(
                    sum(self.vars[(p, day, "AM")] for p in self.req.staff_ids if (p, day, "AM") in self.vars)
                    == needed_am
                )
                self.model.Add(
                    sum(self.vars[(p, day, "PM")] for p in self.req.staff_ids if (p, day, "PM") in self.vars)
                    == needed_pm
                )

                for p in self.req.staff_ids:
                    if (p, day, "24H") in self.vars:
                        self.model.Add(self.vars[(p, day, "24H")] == 0)

            needed_sb = self.config.constraints.standby_per_day
            self.model.Add(
                sum(self.vars[(p, day, "S/B")] for p in self.req.staff_ids if (p, day, "S/B") in self.vars) == needed_sb
            )

    def _apply_fixed_assignments(self):
        for (person, day), value in self.req.fixed_assignments.items():
            if value == "X":
                for shift in self.shifts:
                    if (person, day, shift) in self.vars:
                        self.model.Add(self.vars[(person, day, shift)] == 0)
            elif value in self.shifts:
                v_key = (person, day, value)
                if v_key in self.vars:
                    self.model.Add(self.vars[v_key] == 1)

    def _apply_shift_logic(self):
        # 1. Max one shift per day
        for person in self.req.staff_ids:
            for day in self.days_range:
                daily_vars = [self.vars[(person, day, s)] for s in self.shifts if (person, day, s) in self.vars]
                if daily_vars:
                    self.model.Add(sum(daily_vars) <= 1)

        # 2. Max consecutive duties
        limit = self.config.constraints.max_consecutive_duties
        for person in self.req.staff_ids:
            for i in range(len(self.days_range) - limit):
                window_days = self.days_range[i : i + limit + 1]
                window_vars = []
                for d in window_days:
                    for s in self.shifts:
                        if (person, d, s) in self.vars:
                            window_vars.append(self.vars[(person, d, s)])
                if window_vars:
                    self.model.Add(sum(window_vars) <= limit)

        # 3. Dynamic Transition Rules
        rules = self.config.rules.transitions
        for person in self.req.staff_ids:
            for day in self.days_range:
                next_day = day + 1
                if next_day not in self.days_range:
                    continue

                for prev_shift in self.shifts:
                    for next_shift in self.shifts:
                        if (person, day, prev_shift) not in self.vars or (
                            person,
                            next_day,
                            next_shift,
                        ) not in self.vars:
                            continue

                        status = rules.get(prev_shift, {}).get(next_shift, C.RuleStatus.ALLOWED.value)

                        if status == C.RuleStatus.HARD.value:
                            self.model.AddBoolOr(
                                [
                                    self.vars[(person, day, prev_shift)].Not(),
                                    self.vars[(person, next_day, next_shift)].Not(),
                                ]
                            )
                        elif status == C.RuleStatus.SOFT.value:
                            violation_var = self.model.NewBoolVar(f"soft_ban_{person}_{day}_{prev_shift}_{next_shift}")
                            self.model.AddMultiplicationEquality(
                                violation_var,
                                [self.vars[(person, day, prev_shift)], self.vars[(person, next_day, next_shift)]],
                            )
                            self.soft_ban_penalties.append(violation_var)

    def _apply_fairness_objective(self):
        person_points = []
        SCALE = C.SCORE_SCALE_FACTOR
        SOFT_BAN_WEIGHT = 50 * SCALE

        # --- Catch Up Limit Calculation (Relative) ---
        catch_up_limit = self.config.constraints.catch_up_limit
        max_allowed_points = 0

        if catch_up_limit > 0:
            # 1. Calculate Total Available Points for the month
            # Since manpower needs are Hard Constraints, we can calculate the exact total points
            # the roster MUST generate.
            total_roster_points = 0

            # Helper to look up configured needed count
            def get_needed(shift_type: str) -> int:
                if shift_type == "S/B":
                    return self.config.constraints.standby_per_day
                return self.config.constraints.personnel_needed_per_shift.get(shift_type, 0)

            for (day, shift), weight in self.req.shift_weights.items():
                if day in self.req.inactive_days:
                    continue

                # Check if this shift is active for this day mode
                mode = self.req.day_modes.get(day, C.ScheduleMode.SHIFT.value)
                is_active_shift = False

                if mode == C.ScheduleMode.FULL_24H.value:
                    if shift in ["24H", "S/B"]:
                        is_active_shift = True
                else:  # SHIFT
                    if shift in ["AM", "PM", "S/B"]:
                        is_active_shift = True

                if is_active_shift:
                    count = get_needed(shift)
                    total_roster_points += weight * count

            # 2. Calculate Average
            num_staff = len(self.req.staff_ids)
            if num_staff > 0:
                avg_points = total_roster_points / num_staff
                # 3. Add Limit (Average + Extra Allowed)
                max_allowed_points = int(avg_points + (catch_up_limit * SCALE))
            else:
                max_allowed_points = 0  # Should not happen

        # --- End Catch Up Calculation ---

        for person in self.req.staff_ids:
            expr = []

            # Monthly Points
            for day in self.days_range:
                for shift in self.shifts:
                    if (person, day, shift) not in self.vars:
                        continue
                    weight = self.req.shift_weights.get((day, shift), 0)
                    if weight > 0:
                        expr.append(self.vars[(person, day, shift)] * weight)

            monthly_total = self.model.NewIntVar(0, 10000000, f"month_pts_{person}")
            self.model.Add(monthly_total == sum(expr))

            # **FEATURE: Catch Up Limit (Relative)**
            if catch_up_limit > 0 and max_allowed_points > 0:
                # User cannot exceed Average + Limit
                self.model.Add(monthly_total <= max_allowed_points)

            # Total Points (Carry Over + Month)
            total_pts = self.model.NewIntVar(0, 10000000, f"total_pts_{person}")
            carry_fwd = int(self.prev_balance.get(person, 0.0) * SCALE)
            self.model.Add(total_pts == carry_fwd + monthly_total)

            person_points.append(total_pts)

        if not person_points:
            return

        min_pts = self.model.NewIntVar(0, 10000000, "min_points")
        max_pts = self.model.NewIntVar(0, 10000000, "max_points")

        self.model.AddMinEquality(min_pts, person_points)
        self.model.AddMaxEquality(max_pts, person_points)

        if self.soft_ban_penalties:
            max_penalty = len(self.soft_ban_penalties) * SOFT_BAN_WEIGHT
            total_penalty = self.model.NewIntVar(0, max_penalty, "total_penalty")
            self.model.Add(total_penalty == sum(self.soft_ban_penalties) * SOFT_BAN_WEIGHT)
        else:
            total_penalty = self.model.NewIntVar(0, 0, "total_penalty")
            self.model.Add(total_penalty == 0)

        self.model.Minimize((max_pts - min_pts) + total_penalty)

    def solve(self) -> Optional[Tuple[Dict[Tuple[str, int], str], Any]]:
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.config.constraints.solver_timeout_seconds
        status = solver.Solve(self.model)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            schedule = {}
            for (person, d, shift), var in self.vars.items():
                if solver.Value(var) == 1:
                    key = (person, d)
                    schedule[key] = shift
            return schedule, status

        logger.warning(f"Solver failed. Status: {status}")
        return None
