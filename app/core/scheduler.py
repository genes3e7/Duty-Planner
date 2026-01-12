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

        # Determine number of days from the day_modes map
        self.days_range = sorted(self.req.day_modes.keys())

    def build_model(self):
        """
        Constructs the CP-SAT model: variables, hard constraints, and objective.
        """
        # 1. Early return if no staff
        if not self.req.staff_ids:
            logger.warning("No staff IDs provided. Returning empty model.")
            return

        # 2. Create Variables
        self._create_variables()

        # 3. Apply Hard Constraints
        self._apply_daily_coverage()
        self._apply_fixed_assignments()
        self._apply_shift_logic()

        # 4. Apply Fairness Objective
        self._apply_fairness_objective()

    def _create_variables(self):
        """Creates boolean variables for each person, day, and shift."""
        for person in self.req.staff_ids:
            for day in self.days_range:
                if day in self.req.inactive_days:
                    continue

                for shift in self.shifts:
                    # Var name: "Person_Day_Shift"
                    self.vars[(person, day, shift)] = self.model.NewBoolVar(f"{person}_{day}_{shift}")

    def _apply_daily_coverage(self):
        """Ensures the required number of people are assigned to each shift type."""
        for day in self.days_range:
            if day in self.req.inactive_days:
                continue

            mode = self.req.day_modes.get(day, C.ScheduleMode.SHIFT.value)

            if mode == C.ScheduleMode.FULL_24H.value:
                # 24H Mode: Need 24H and S/B
                needed_24h = self.config.constraints.personnel_needed_per_shift.get("24H", 1)
                self.model.Add(
                    sum(self.vars[(p, day, "24H")] for p in self.req.staff_ids if (p, day, "24H") in self.vars)
                    == needed_24h
                )

                # AM/PM must be 0
                for p in self.req.staff_ids:
                    if (p, day, "AM") in self.vars:
                        self.model.Add(self.vars[(p, day, "AM")] == 0)
                    if (p, day, "PM") in self.vars:
                        self.model.Add(self.vars[(p, day, "PM")] == 0)

            else:
                # SHIFT Mode: Need AM and PM
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

                # 24H must be 0
                for p in self.req.staff_ids:
                    if (p, day, "24H") in self.vars:
                        self.model.Add(self.vars[(p, day, "24H")] == 0)

            # S/B coverage (applies to both modes usually, or configured)
            needed_sb = self.config.constraints.standby_per_day
            self.model.Add(
                sum(self.vars[(p, day, "S/B")] for p in self.req.staff_ids if (p, day, "S/B") in self.vars) == needed_sb
            )

    def _apply_fixed_assignments(self):
        """
        Forces variables to 1 based on UI grid inputs (X, AM, PM, etc.).
        """
        for (person, day), value in self.req.fixed_assignments.items():
            if value == "X":
                # Person cannot work ANY shift on this day
                for shift in self.shifts:
                    if (person, day, shift) in self.vars:
                        self.model.Add(self.vars[(person, day, shift)] == 0)
            elif value in self.shifts:
                # Must work exactly this shift
                v_key = (person, day, value)
                if v_key in self.vars:
                    self.model.Add(self.vars[v_key] == 1)
                else:
                    mode = self.req.day_modes.get(day, "UNKNOWN")
                    raise ValueError(
                        f"Fixed assignment error: Cannot assign '{value}' to {person} on Day {day} "
                        f"(Mode: {mode}). Variable does not exist."
                    )

    def _apply_shift_logic(self):
        """
        Applies logic rules:
        1. Max one shift per day per person.
        2. No consecutive duties limit.
        3. Cannot work if worked 24H yesterday.
        4. No duty -> Heavy (24H/SB) -> No duty logic.
        """
        # 1. Max one shift per day
        for person in self.req.staff_ids:
            for day in self.days_range:
                daily_vars = [self.vars[(person, day, s)] for s in self.shifts if (person, day, s) in self.vars]
                if daily_vars:
                    self.model.Add(sum(daily_vars) <= 1)

        # 2. No work after 24H (Explicit)
        # This is strictly for "24H" -> Empty Day.
        for person in self.req.staff_ids:
            for day in self.days_range:
                if (person, day, "24H") in self.vars:
                    next_day = day + 1
                    if next_day in self.days_range:
                        for shift in self.shifts:
                            if (person, next_day, shift) in self.vars:
                                self.model.AddBoolOr(
                                    [
                                        self.vars[(person, day, "24H")].Not(),
                                        self.vars[(person, next_day, shift)].Not(),
                                    ]
                                )

        # 3. Max consecutive duties
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

        # 4. Strict Isolation for S/B and 24H
        # "Heavy" duties (24H, S/B) must be surrounded by rest days (no duties).
        # This implies:
        #   - Day D (Heavy) => Day D-1 (Rest)
        #   - Day D (Heavy) => Day D+1 (Rest)
        # We iterate through all days. If a day is Heavy, neighbors must be empty.

        heavy_shifts = ["24H", "S/B"]

        for person in self.req.staff_ids:
            for day in self.days_range:
                # Check if this day has a potential heavy shift
                day_heavy_vars = [self.vars[(person, day, s)] for s in heavy_shifts if (person, day, s) in self.vars]

                if not day_heavy_vars:
                    continue

                # If any heavy shift is assigned on Day D...
                is_heavy_day = self.model.NewBoolVar(f"{person}_is_heavy_d{day}")
                self.model.Add(sum(day_heavy_vars) >= 1).OnlyEnforceIf(is_heavy_day)
                self.model.Add(sum(day_heavy_vars) == 0).OnlyEnforceIf(is_heavy_day.Not())

                # ... then Day D+1 must be empty (No Shift)
                next_day = day + 1
                if next_day in self.days_range:
                    next_day_shifts = [
                        self.vars[(person, next_day, s)] for s in self.shifts if (person, next_day, s) in self.vars
                    ]
                    if next_day_shifts:
                        self.model.Add(sum(next_day_shifts) == 0).OnlyEnforceIf(is_heavy_day)

                # ... and Day D-1 must be empty (No Shift)
                prev_day = day - 1
                if prev_day in self.days_range:
                    prev_day_shifts = [
                        self.vars[(person, prev_day, s)] for s in self.shifts if (person, prev_day, s) in self.vars
                    ]
                    if prev_day_shifts:
                        self.model.Add(sum(prev_day_shifts) == 0).OnlyEnforceIf(is_heavy_day)

    def _apply_fairness_objective(self):
        """
        Minimizes the difference between max and min points across all staff.
        Uses exact weights passed from Logic layer to account for Multipliers.
        """
        person_points = []

        # Scaling factor matching logic.py (preserves decimal precision)
        SCALE = 100

        for person in self.req.staff_ids:
            expr = []
            # Add Previous Balance (Scaled)
            expr.append(int(self.prev_balance.get(person, 0.0) * SCALE))

            for day in self.days_range:
                for shift in self.shifts:
                    if (person, day, shift) not in self.vars:
                        continue

                    # Use EXACT pre-calculated weight (includes PH/Weekend/Friday multipliers)
                    weight = self.req.shift_weights.get((day, shift), 0)

                    if weight > 0:
                        expr.append(self.vars[(person, day, shift)] * weight)

            person_total = self.model.NewIntVar(0, 10000000, f"total_pts_{person}")
            self.model.Add(person_total == sum(expr))
            person_points.append(person_total)

        if not person_points:
            return

        # Minimize (Max - Min)
        min_pts = self.model.NewIntVar(0, 10000000, "min_points")
        max_pts = self.model.NewIntVar(0, 10000000, "max_points")

        self.model.AddMinEquality(min_pts, person_points)
        self.model.AddMaxEquality(max_pts, person_points)

        self.model.Minimize(max_pts - min_pts)

    def solve(self) -> Optional[Tuple[Dict[Tuple[str, int], str], Any]]:
        """Runs the solver and returns the schedule."""
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.config.constraints.solver_timeout_seconds

        status = solver.Solve(self.model)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            schedule = {}
            for (person, d, shift), var in self.vars.items():
                if solver.Value(var) == 1:
                    key = (person, d)
                    if key in schedule:
                        raise RuntimeError(f"Multiple shifts assigned for {key}: {schedule[key]} and {shift}")
                    schedule[key] = shift
            return schedule, status

        logger.warning(f"Solver failed to find solution. Status: {status}")
        return None
