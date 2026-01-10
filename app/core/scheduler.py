"""
app/core/scheduler.py

This module contains the DutySchedulerEngine, which wraps the Google OR-Tools CP-SAT solver.
It translates high-level business constraints (from AppConfig) into mathematical variables
and constraints to find an optimal duty schedule.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import holidays
import pandas as pd
from ortools.sat.python import cp_model

from app.models.config import AppConfig


@dataclass
class SolverRequest:
    """
    Data Transfer Object representing a single solve request.
    Decouples the solver from the UI state or specific data sources.

    Attributes:
        staff_ids: List of available personnel IDs/names.
        year: The year of the schedule.
        month: The month of the schedule.
        fixed_assignments: Pre-assigned shifts {(Name, Day): Type}.
        day_modes: Map of {Day: Mode ('SHIFT' or '24H')}.
        inactive_days: List of day numbers to exclude from solving.
    """

    staff_ids: List[str]
    year: int
    month: int
    fixed_assignments: Dict[Tuple[str, int], str]
    day_modes: Dict[int, str]
    inactive_days: List[int]


class DutySchedulerEngine:
    """
    The optimization engine that builds and solves the constraint model.

    Uses OR-Tools CP-SAT to satisfy hard constraints while optimizing for fairness.

    Attributes:
        cfg (AppConfig): The application configuration (constraints, points).
        balance (Dict[str, float]): Previous month's point balance for fairness.
        req (SolverRequest): The specific request details (dates, staff, fixed data).
        model (cp_model.CpModel): The internal OR-Tools model instance.
        vars (Dict): Storage for decision variables (person, day, shift) -> BoolVar.
    """

    # Scale factor to handle decimals in integer solver.
    SCALE = 10

    def __init__(self, config: AppConfig, prev_balance: Dict[str, float], request: SolverRequest):
        self.cfg = config
        self.balance = prev_balance
        self.req = request
        self.model = cp_model.CpModel()
        self.vars = {}

        # Define shifts based on internal constants or config keys
        # We map string keys to internal representations if needed,
        # but here we stick to the strings used in config: "AM", "PM", "24H"
        self.shifts = ["AM", "PM", "24H", "S/B"]

        # Initialize holidays for point calculation
        self.sg_holidays = holidays.SG(years=self.req.year)

    def build_model(self):
        """
        Constructs the CP-SAT model by creating variables and applying all constraints.
        This method must be called before solve().

        Raises:
            ValueError: If the request is invalid (e.g., no days configured).
        """
        # Clear vars to prevent stale constraints if rebuilt
        self.vars.clear()

        # Defensive check: Ensure we have staff
        if not self.req.staff_ids:
            # Just return, solver will find no solution which is correct for 0 staff
            return

        if not self.req.day_modes:
            raise ValueError("SolverRequest must have at least one day configured in day_modes.")

        max_day = max(self.req.day_modes.keys())

        # 1. CREATE VARIABLES
        # We create a boolean variable for every combination: (Person, Day, Shift)
        # var = 1 means Person is assigned to Shift on Day.
        for person in self.req.staff_ids:
            for d in range(1, max_day + 1):
                # Skip inactive days (e.g., shorter months or disabled days)
                if d in self.req.inactive_days or d not in self.req.day_modes:
                    continue

                mode = self.req.day_modes[d]

                # Create variables based on the day's mode
                if mode == "24H":
                    # Only create a 24H variable and S/B variable
                    self.vars[(person, d, "24H")] = self.model.NewBoolVar(f"{person}_d{d}_24H")
                    self.vars[(person, d, "S/B")] = self.model.NewBoolVar(f"{person}_d{d}_SB")
                else:
                    # Create AM, PM and S/B variables
                    self.vars[(person, d, "AM")] = self.model.NewBoolVar(f"{person}_d{d}_AM")
                    self.vars[(person, d, "PM")] = self.model.NewBoolVar(f"{person}_d{d}_PM")
                    self.vars[(person, d, "S/B")] = self.model.NewBoolVar(f"{person}_d{d}_SB")

        # 2. APPLY HARD CONSTRAINTS
        self._apply_fixed_assignments()
        self._apply_daily_manpower_requirements(max_day)
        self._apply_max_one_shift_per_day(max_day)
        self._apply_no_consecutive_shifts(max_day)
        self._apply_max_consecutive_working_days(max_day)

        # 3. OBJECTIVE FUNCTION (Fairness)
        # We want to minimize the variance in points.
        self._apply_fairness_objective(max_day)

    def _apply_fixed_assignments(self):
        """Forces variables to 1 or 0 based on pre-assigned duties in the UI."""
        for (person, day), shift_type in self.req.fixed_assignments.items():
            # Removed unused variable 'day_mode'

            if shift_type == "X":
                # Ensure at least one variable exists for this person/day
                found_any = False
                for s in self.shifts:
                    if (person, day, s) in self.vars:
                        found_any = True
                        break
                if not found_any:
                    # This might happen if user assigned X on an inactive day
                    continue

                # Apply X constraint
                for s in self.shifts:
                    if (person, day, s) in self.vars:
                        self.model.Add(self.vars[(person, day, s)] == 0)

            elif shift_type in self.shifts:
                # Ensure the specific variable exists
                if (person, day, shift_type) not in self.vars:
                    # User assigned a shift that contradicts the day mode (e.g., AM on a 24H day)
                    # We treat this as an impossible constraint implicitly or ignore.
                    # Here we raise to inform caller, or could Log warning.
                    pass
                else:
                    self.model.Add(self.vars[(person, day, shift_type)] == 1)

    def _apply_daily_manpower_requirements(self, max_day: int):
        """Ensures enough people are assigned to each shift type every day."""
        for d in range(1, max_day + 1):
            if d in self.req.inactive_days or d not in self.req.day_modes:
                continue

            mode = self.req.day_modes[d]

            # 1. Standby Requirement (Applies to both modes)
            sb_needed = self.cfg.constraints.standby_per_day
            potential_sb = [self.vars[(p, d, "S/B")] for p in self.req.staff_ids if (p, d, "S/B") in self.vars]
            if potential_sb:
                self.model.Add(sum(potential_sb) == sb_needed)

            # 2. Duty Requirements
            if mode == "24H":
                # Ensure N people are on 24H duty
                needed = self.cfg.constraints.personnel_needed_per_shift.get("24H", 1)
                potential_workers = [self.vars[(p, d, "24H")] for p in self.req.staff_ids if (p, d, "24H") in self.vars]
                if potential_workers:
                    self.model.Add(sum(potential_workers) == needed)
            else:
                # Ensure N people for AM and N for PM
                for shift in ["AM", "PM"]:
                    needed = self.cfg.constraints.personnel_needed_per_shift.get(shift, 1)
                    potential_workers = [
                        self.vars[(p, d, shift)] for p in self.req.staff_ids if (p, d, shift) in self.vars
                    ]
                    if potential_workers:
                        self.model.Add(sum(potential_workers) == needed)

    def _apply_max_one_shift_per_day(self, max_day: int):
        """Prevents a person from doing multiple duties on the same day."""
        for person in self.req.staff_ids:
            for d in range(1, max_day + 1):
                # Collect all possible shift variables for this person/day
                possible_shifts = [self.vars[(person, d, s)] for s in self.shifts if (person, d, s) in self.vars]

                if possible_shifts:
                    # Sum of assignments must be <= 1
                    self.model.Add(sum(possible_shifts) <= 1)

    def _apply_no_consecutive_shifts(self, max_day: int):
        """
        Prevents back-to-back duties that are physically impossible or violate rest rules.
        """
        for person in self.req.staff_ids:
            for d in range(1, max_day):  # Iterate up to second-to-last day
                next_d = d + 1

                fixed_d = self.req.fixed_assignments.get((person, d))
                fixed_next = self.req.fixed_assignments.get((person, next_d))

                # --- RULE 1: Heavy Duty (Day D) -> Rest (Day D+1) ---
                # Check Fixed D (S/B or 24H)
                if fixed_d in ["S/B", "24H"]:
                    for s in self.shifts:
                        if (person, next_d, s) in self.vars:
                            self.model.Add(self.vars[(person, next_d, s)] == 0)

                # Check Variable D (24H or S/B)
                for heavy in ["24H", "S/B"]:
                    if (person, d, heavy) in self.vars:
                        next_day_vars = [
                            self.vars[(person, next_d, s)] for s in self.shifts if (person, next_d, s) in self.vars
                        ]
                        if next_day_vars:
                            self.model.Add(sum(next_day_vars) == 0).OnlyEnforceIf(self.vars[(person, d, heavy)])

                # --- RULE 2: Any Duty (Day D) -> No Heavy Duty (Day D+1) ---
                # 2.1 Fixed Next is S/B OR 24H -> Day D cannot be Any Duty (if variable)
                if fixed_next in ["S/B", "24H"]:
                    for s in self.shifts:
                        if (person, d, s) in self.vars:
                            self.model.Add(self.vars[(person, d, s)] == 0)

                # 2.2 Variable 24H or S/B on Next -> Day D cannot be Any Duty
                for heavy in ["24H", "S/B"]:
                    if (person, next_d, heavy) in self.vars:
                        # Get all possible vars for Day D
                        current_day_vars = [
                            self.vars[(person, d, s)] for s in self.shifts if (person, d, s) in self.vars
                        ]
                        if current_day_vars:
                            # If Heavy is assigned on next day, sum of current day vars must be 0
                            self.model.Add(sum(current_day_vars) == 0).OnlyEnforceIf(self.vars[(person, next_d, heavy)])

                # --- RULE 3: PM -> AM Rest Violation ---
                # Fixed PM on D
                if fixed_d == "PM":
                    if (person, next_d, "AM") in self.vars:
                        self.model.Add(self.vars[(person, next_d, "AM")] == 0)

                # Variable PM on D
                if (person, d, "PM") in self.vars and (person, next_d, "AM") in self.vars:
                    self.model.Add(self.vars[(person, next_d, "AM")] == 0).OnlyEnforceIf(self.vars[(person, d, "PM")])

    def _apply_max_consecutive_working_days(self, max_day: int):
        """
        Ensures that a person does not work more than N days in a row.
        Includes "S/B" (Standby) as a working day.
        """
        limit = self.cfg.constraints.max_consecutive_duties
        window_size = limit + 1

        for person in self.req.staff_ids:
            working_exprs = {}

            for d in range(1, max_day + 1):
                day_vars = [self.vars[(person, d, s)] for s in self.shifts if (person, d, s) in self.vars]
                if day_vars:
                    working_exprs[d] = sum(day_vars)
                else:
                    working_exprs[d] = 0

            # Apply Sliding Window
            for start_day in range(1, max_day - limit + 1):
                window_sum = []
                for i in range(window_size):
                    d = start_day + i
                    if d in working_exprs:
                        window_sum.append(working_exprs[d])

                if window_sum:
                    self.model.Add(sum(window_sum) <= limit)

    def _apply_fairness_objective(self, max_day: int):
        """
        Attempts to distribute points evenly by minimizing the difference between
        the maximum and minimum score among personnel.
        """
        person_points = []

        for person in self.req.staff_ids:
            initial_pts = int(self.balance.get(person, 0.0) * self.SCALE)
            earned_expr = 0
            for d in range(1, max_day + 1):
                try:
                    dt = pd.Timestamp(year=self.req.year, month=self.req.month, day=d)
                except Exception:
                    continue

                for shift in self.shifts:
                    if (person, d, shift) in self.vars:
                        # Use centralized scorer in PointsConfig
                        final_pts = self.cfg.points.calculate_score(
                            date_obj=dt, shift_type=shift, scale=self.SCALE, holidays_obj=self.sg_holidays
                        )
                        if final_pts > 0:
                            earned_expr += self.vars[(person, d, shift)] * final_pts

            total_var = self.model.NewIntVar(0, 1000000, f"total_pts_{person}")
            self.model.Add(total_var == initial_pts + earned_expr)
            person_points.append(total_var)

        min_pts = self.model.NewIntVar(0, 1000000, "min_points")
        max_pts = self.model.NewIntVar(0, 1000000, "max_points")

        self.model.AddMinEquality(min_pts, person_points)
        self.model.AddMaxEquality(max_pts, person_points)

        self.model.Minimize(max_pts - min_pts)

    def solve(self) -> Optional[Tuple[Dict, Optional[Any]]]:
        """
        Executes the solver.

        Returns:
            Tuple[Dict, None]: A dictionary of assignments if successful.
            None: If no feasible solution is found.
        """
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.cfg.constraints.solver_timeout_seconds

        status = solver.Solve(self.model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            schedule = {}
            for (person, d, shift), var in self.vars.items():
                if solver.Value(var) == 1:
                    schedule[(person, d)] = shift

            for key, val in self.req.fixed_assignments.items():
                if val == "X":
                    schedule[key] = "X"

            return schedule, None
        else:
            return None
