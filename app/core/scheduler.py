"""
app/core/scheduler.py

This module contains the DutySchedulerEngine, which wraps the Google OR-Tools CP-SAT solver.
It translates high-level business constraints (from AppConfig) into mathematical variables
and constraints to find an optimal duty schedule.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ortools.sat.python import cp_model

from app.models.config import AppConfig


@dataclass
class SolverRequest:
    """
    Data Transfer Object representing a single solve request.
    Decouples the solver from the UI state or specific data sources.
    """

    staff_ids: List[str]
    year: int
    month: int
    fixed_assignments: Dict[Tuple[str, int], str]  # (Person, Day) -> ShiftType
    day_modes: Dict[int, str]  # Day -> "SHIFT" or "24H"
    inactive_days: List[int]  # Days excluded from planning


class DutySchedulerEngine:
    """
    The optimization engine that builds and solves the constraint model.

    Attributes:
        cfg (AppConfig): The application configuration (constraints, points).
        balance (Dict[str, float]): Previous month's point balance for fairness.
        req (SolverRequest): The specific request details (dates, staff, fixed data).
        model (cp_model.CpModel): The internal OR-Tools model instance.
        vars (Dict): Storage for decision variables (person, day, shift) -> BoolVar.
    """

    def __init__(self, config: AppConfig, prev_balance: Dict[str, float], request: SolverRequest):
        self.cfg = config
        self.balance = prev_balance
        self.req = request
        self.model = cp_model.CpModel()
        self.vars = {}

        # Define shifts based on internal constants or config keys
        # We map string keys to internal representations if needed,
        # but here we stick to the strings used in config: "AM", "PM", "24H"
        self.shifts = ["AM", "PM", "24H"]

    def build_model(self):
        """
        Constructs the CP-SAT model by creating variables and applying all constraints.
        This method must be called before solve().
        """
        # In a real dynamic month scenario, get max day from request or calendar
        # For safety, we can scan the request's day_modes keys
        if self.req.day_modes:
            max_day = max(self.req.day_modes.keys())
        else:
            max_day = 31

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
                    # Only create a 24H variable
                    self.vars[(person, d, "24H")] = self.model.NewBoolVar(f"{person}_d{d}_24H")
                else:
                    # Create AM and PM variables
                    self.vars[(person, d, "AM")] = self.model.NewBoolVar(f"{person}_d{d}_AM")
                    self.vars[(person, d, "PM")] = self.model.NewBoolVar(f"{person}_d{d}_PM")

        # 2. APPLY HARD CONSTRAINTS
        self._apply_fixed_assignments()
        self._apply_daily_manpower_requirements(max_day)
        self._apply_max_one_shift_per_day(max_day)
        self._apply_no_consecutive_shifts(max_day)

        # 3. OBJECTIVE FUNCTION (Fairness)
        # We want to minimize the variance in points.
        self._apply_fairness_objective(max_day)

    def _apply_fixed_assignments(self):
        """Forces variables to 1 or 0 based on pre-assigned duties in the UI."""
        for (person, day), shift_type in self.req.fixed_assignments.items():
            # Handle "X" (Leave/Unavailable) -> Force ALL shifts on this day to 0
            if shift_type == "X":
                for s in self.shifts:
                    if (person, day, s) in self.vars:
                        self.model.Add(self.vars[(person, day, s)] == 0)

            # Handle Specific Duty (AM/PM/24H) -> Force that specific var to 1
            elif (person, day, shift_type) in self.vars:
                self.model.Add(self.vars[(person, day, shift_type)] == 1)

    def _apply_daily_manpower_requirements(self, max_day: int):
        """Ensures enough people are assigned to each shift type every day."""
        for d in range(1, max_day + 1):
            if d in self.req.inactive_days or d not in self.req.day_modes:
                continue

            mode = self.req.day_modes[d]

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
        """Prevents a person from doing AM and PM on the same day (if valid)."""
        for person in self.req.staff_ids:
            for d in range(1, max_day + 1):
                # If both AM and PM variables exist for this day/person
                if (person, d, "AM") in self.vars and (person, d, "PM") in self.vars:
                    # Sum of assignments must be <= 1
                    self.model.Add(self.vars[(person, d, "AM")] + self.vars[(person, d, "PM")] <= 1)

    def _apply_no_consecutive_shifts(self, max_day: int):
        """
        Prevents back-to-back duties that are physically impossible or violate rest rules.
        e.g., PM today -> AM tomorrow.
        """
        for person in self.req.staff_ids:
            for d in range(1, max_day):  # Iterate up to second-to-last day
                next_d = d + 1

                # Case 1: PM today -> AM tomorrow (Rest violation)
                if (person, d, "PM") in self.vars and (person, next_d, "AM") in self.vars:
                    self.model.AddBoolOr([self.vars[(person, d, "PM")].Not(), self.vars[(person, next_d, "AM")].Not()])

                # Case 2: 24H today -> AM/PM/24H tomorrow (Gap rule)
                # If you do 24H, you usually need the next day off.
                if (person, d, "24H") in self.vars:
                    # Collect all possible shifts for the next day
                    next_day_shifts = []
                    for s in self.shifts:
                        if (person, next_d, s) in self.vars:
                            next_day_shifts.append(self.vars[(person, next_d, s)])

                    if next_day_shifts:
                        # If 24H today is True, then SUM(next_day_shifts) must be 0
                        self.model.Add(sum(next_day_shifts) == 0).OnlyEnforceIf(self.vars[(person, d, "24H")])

    def _apply_fairness_objective(self, max_day: int):
        """
        Attempts to distribute points evenly.
        We calculate total points per person and minimize the difference between the
        highest and lowest scorer.
        """
        person_points = []

        for person in self.req.staff_ids:
            # Scale points by 10 to handle decimals in integer solver
            SCALE = 10

            initial_pts = int(self.balance.get(person, 0.0) * SCALE)

            # Sum of points earned this month
            earned_expr = 0
            for d in range(1, max_day + 1):
                for shift in self.shifts:
                    if (person, d, shift) in self.vars:
                        # Get base points from config
                        base = self.cfg.points.get_by_type(shift)

                        # Apply naive multiplier check (simplified for performance)
                        pts_val = int(base * SCALE)

                        earned_expr += self.vars[(person, d, shift)] * pts_val

            # Total for person
            total_var = self.model.NewIntVar(0, 10000, f"total_pts_{person}")
            self.model.Add(total_var == initial_pts + earned_expr)
            person_points.append(total_var)

        # Minimize (Max - Min)
        min_pts = self.model.NewIntVar(0, 10000, "min_points")
        max_pts = self.model.NewIntVar(0, 10000, "max_points")

        self.model.AddMinEquality(min_pts, person_points)
        self.model.AddMaxEquality(max_pts, person_points)

        self.model.Minimize(max_pts - min_pts)

    def solve(self) -> Optional[Tuple[Dict, Any]]:
        """
        Executes the solver.

        Returns:
            Tuple: (ScheduleDict, SummaryStats) if feasible.
            None: If no solution found.

            ScheduleDict format: {(Person, Day): ShiftString}
        """
        solver = cp_model.CpSolver()
        # Optional: Set time limit
        solver.parameters.max_time_in_seconds = 10.0

        status = solver.Solve(self.model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            schedule = {}
            for (person, d, shift), var in self.vars.items():
                if solver.Value(var) == 1:
                    # We found an assignment
                    schedule[(person, d)] = shift

            # We also return fixed assignments (X) that weren't variables
            for key, val in self.req.fixed_assignments.items():
                if val == "X":
                    schedule[key] = "X"

            return schedule, None
        else:
            return None
