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
        # 1. Early return if no staff
        if not self.req.staff_ids:
            logger.warning("No staff IDs provided. Returning empty model.")
            return

        # 2. Create Variables
        self._create_variables()

        # 3. Apply Hard Constraints & Soft Bans
        self._apply_daily_coverage()
        self._apply_fixed_assignments()
        self._apply_shift_logic()

        # 4. Apply Fairness Objective (incorporating Soft Bans)
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
        2. Max consecutive duties.
        3. Transition Rules (Hard Bans & Soft Bans).
        """
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

        # 3. Transition Logic (Hard Bans & Soft Bans)
        # Forbidden pairs: (Day D Shift, Day D+1 Shift) -> Strictly prevented
        forbidden_transitions = [
            ("PM", "PM"),
            ("PM", "24H"),
            ("24H", "AM"),
            ("24H", "24H"),
            ("24H", "S/B"),
            ("S/B", "24H"),
        ]

        # Soft Ban pairs: (Day D Shift, Day D+1 Shift) -> Discouraged via penalty
        soft_ban_transitions = [
            ("AM", "PM"),
            ("PM", "AM"),
            ("PM", "S/B"),  # Fixed: SB -> S/B
            ("S/B", "AM"),  # Fixed: SB -> S/B
            ("S/B", "S/B"),  # Fixed: SB -> S/B
        ]

        for person in self.req.staff_ids:
            for day in self.days_range:
                next_day = day + 1
                if next_day not in self.days_range:
                    continue

                # --- Handle Hard Bans ---
                for prev_shift, next_shift in forbidden_transitions:
                    if (person, day, prev_shift) in self.vars and (person, next_day, next_shift) in self.vars:
                        # Logic: NOT (Prev AND Next)
                        self.model.AddBoolOr(
                            [
                                self.vars[(person, day, prev_shift)].Not(),
                                self.vars[(person, next_day, next_shift)].Not(),
                            ]
                        )

                # --- Handle Soft Bans ---
                for prev_shift, next_shift in soft_ban_transitions:
                    if (person, day, prev_shift) in self.vars and (person, next_day, next_shift) in self.vars:
                        # Create a boolean variable that is True ONLY if this bad transition occurs
                        violation_var = self.model.NewBoolVar(f"soft_ban_{person}_{day}_{prev_shift}_{next_shift}")

                        # violation_var <=> (Prev AND Next)
                        # This utility function forces violation_var to 1 if both conditions are met, else 0
                        self.model.AddMultiplicationEquality(
                            violation_var,
                            [self.vars[(person, day, prev_shift)], self.vars[(person, next_day, next_shift)]],
                        )

                        self.soft_ban_penalties.append(violation_var)

    def _apply_fairness_objective(self):
        """
        Minimizes (Max Points - Min Points) + (Soft Ban Penalties).
        """
        person_points = []
        SCALE = 100

        # High penalty to discourage soft bans (equivalent to 50 points difference)
        SOFT_BAN_WEIGHT = 50 * SCALE

        for person in self.req.staff_ids:
            expr = []
            expr.append(int(self.prev_balance.get(person, 0.0) * SCALE))

            for day in self.days_range:
                for shift in self.shifts:
                    if (person, day, shift) not in self.vars:
                        continue
                    weight = self.req.shift_weights.get((day, shift), 0)
                    if weight > 0:
                        expr.append(self.vars[(person, day, shift)] * weight)

            person_total = self.model.NewIntVar(0, 10000000, f"total_pts_{person}")
            self.model.Add(person_total == sum(expr))
            person_points.append(person_total)

        if not person_points:
            return

        min_pts = self.model.NewIntVar(0, 10000000, "min_points")
        max_pts = self.model.NewIntVar(0, 10000000, "max_points")

        self.model.AddMinEquality(min_pts, person_points)
        self.model.AddMaxEquality(max_pts, person_points)

        # Calculate total penalty from soft bans safely
        if self.soft_ban_penalties:
            max_penalty = len(self.soft_ban_penalties) * SOFT_BAN_WEIGHT
            total_penalty = self.model.NewIntVar(0, max_penalty, "total_penalty")
            self.model.Add(total_penalty == sum(self.soft_ban_penalties) * SOFT_BAN_WEIGHT)
        else:
            total_penalty = self.model.NewIntVar(0, 0, "total_penalty")
            self.model.Add(total_penalty == 0)

        # Minimize Fairness Gap + Penalties
        # This ensures stats remain accurate (based on person_points), but solver choice is influenced by penalty
        self.model.Minimize((max_pts - min_pts) + total_penalty)

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
