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

# --- FIXED IMPORT ---
from app.utils.helpers import get_base_shift_type, get_shift_name

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
        """
        Initializes the SolverRequest.

        Args:
            staff_ids: List of available staff names.
            year: The target year.
            month: The target month.
            fixed_assignments: Dictionary of (Name, Day) -> Shift Value pre-locked by user.
            day_modes: Dictionary of Day -> Mode (SHIFT or 24H).
            inactive_days: List of day numbers that are inactive.
            shift_weights: Dictionary of (Day, Shift) -> Scaled Integer Points.
        """
        self.staff_ids = staff_ids
        self.year = year
        self.month = month
        self.fixed_assignments = fixed_assignments
        self.day_modes = day_modes
        self.inactive_days = inactive_days
        self.shift_weights = shift_weights


class DutySchedulerEngine:
    """
    The main engine wrapping Google OR-Tools CP-SAT solver.
    Orchestrates variable creation, constraint application, and solving.
    """

    def __init__(self, config: AppConfig, prev_balance: Dict[str, float], request: SolverRequest):
        """
        Initializes the scheduler engine.

        Args:
            config: The application configuration (rules, points, constraints).
            prev_balance: Dictionary of previous month's carry-over points per person.
            request: The solver request data object.
        """
        self.config = config
        self.prev_balance = prev_balance
        self.req = request
        self.model = cp_model.CpModel()
        self.vars: Dict[Tuple[str, int, str], Any] = {}

        # New: Store team counts
        self.active_teams = config.constraints.num_active_teams
        self.sb_teams = config.constraints.num_standby_teams

        # Determine number of days from the day_modes map
        self.days_range = sorted(self.req.day_modes.keys())
        self.soft_ban_penalties: List[Any] = []  # Stores penalty variables for soft bans

    def build_model(self):
        """
        Constructs the CP-SAT model by calling internal methods to create variables,
        apply hard constraints, shift logic, and the fairness objective.
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
        """
        Creates boolean decision variables for each person, day, and shift.
        Stores them in self.vars[(person, day, shift)].
        """
        for person in self.req.staff_ids:
            for day in self.days_range:
                if day in self.req.inactive_days:
                    continue

                # Create Active Team Vars
                for t in range(1, self.active_teams + 1):
                    for base in ["AM", "PM", "24H"]:
                        s_name = get_shift_name(base, t)
                        self.vars[(person, day, s_name)] = self.model.NewBoolVar(f"{person}_{day}_{s_name}")

                # Create Standby Team Vars
                for t in range(1, self.sb_teams + 1):
                    s_name = get_shift_name("S/B", t)
                    self.vars[(person, day, s_name)] = self.model.NewBoolVar(f"{person}_{day}_{s_name}")

    def _apply_daily_coverage(self):
        """
        Applies Hard Constraint: Daily Coverage.
        Ensures the required number of people are assigned to each shift type (AM, PM, 24H, S/B)
        based on the day's mode (SHIFT vs 24H) and configuration.
        Iterates through every Active Team and Standby Team instance.
        """
        for day in self.days_range:
            if day in self.req.inactive_days:
                continue

            mode = self.req.day_modes.get(day, C.ScheduleMode.SHIFT.value)

            # --- 1. Active Teams Coverage ---
            for t in range(1, self.active_teams + 1):
                am_name = get_shift_name("AM", t)
                pm_name = get_shift_name("PM", t)
                h24_name = get_shift_name("24H", t)

                if mode == C.ScheduleMode.FULL_24H.value:
                    # Require 24H staff
                    needed_24h = self.config.constraints.personnel_needed_per_shift.get("24H", 1)
                    self.model.Add(
                        sum(
                            self.vars[(p, day, h24_name)] for p in self.req.staff_ids if (p, day, h24_name) in self.vars
                        )
                        == needed_24h
                    )
                    # Force AM/PM to 0 for this team
                    for p in self.req.staff_ids:
                        if (p, day, am_name) in self.vars:
                            self.model.Add(self.vars[(p, day, am_name)] == 0)
                        if (p, day, pm_name) in self.vars:
                            self.model.Add(self.vars[(p, day, pm_name)] == 0)

                else:  # SHIFT Mode
                    # Require AM staff
                    needed_am = self.config.constraints.personnel_needed_per_shift.get("AM", 1)
                    self.model.Add(
                        sum(self.vars[(p, day, am_name)] for p in self.req.staff_ids if (p, day, am_name) in self.vars)
                        == needed_am
                    )
                    # Require PM staff
                    needed_pm = self.config.constraints.personnel_needed_per_shift.get("PM", 1)
                    self.model.Add(
                        sum(self.vars[(p, day, pm_name)] for p in self.req.staff_ids if (p, day, pm_name) in self.vars)
                        == needed_pm
                    )
                    # Force 24H to 0 for this team
                    for p in self.req.staff_ids:
                        if (p, day, h24_name) in self.vars:
                            self.model.Add(self.vars[(p, day, h24_name)] == 0)

            # --- 2. Standby Teams Coverage ---
            needed_sb = self.config.constraints.standby_per_day
            for t in range(1, self.sb_teams + 1):
                sb_name = get_shift_name("S/B", t)
                self.model.Add(
                    sum(self.vars[(p, day, sb_name)] for p in self.req.staff_ids if (p, day, sb_name) in self.vars)
                    == needed_sb
                )

    def _apply_fixed_assignments(self):
        """
        Applies Hard Constraint: Fixed Assignments.
        Locks specific cells to values provided by the user (e.g., 'X', 'AM', 'AM_2').
        """
        for (person, day), value in self.req.fixed_assignments.items():
            if value == "X":
                # Ban ALL possible shifts for this day
                all_shifts = self._get_all_shift_keys()
                for shift in all_shifts:
                    if (person, day, shift) in self.vars:
                        self.model.Add(self.vars[(person, day, shift)] == 0)
            elif value:
                # Value matches a specific shift key (e.g. AM, AM_2)
                v_key = (person, day, value)
                if v_key in self.vars:
                    self.model.Add(self.vars[v_key] == 1)

    def _apply_shift_logic(self):
        """
        Applies Physiological and Policy Constraints:
        1. Max one shift per day per person.
        2. Max consecutive working days.
        3. Dynamic Transition Rules (Hard/Soft bans) from configuration.
        """
        all_shifts = self._get_all_shift_keys()

        # 1. Max one shift per day
        for person in self.req.staff_ids:
            for day in self.days_range:
                daily_vars = [self.vars[(person, day, s)] for s in all_shifts if (person, day, s) in self.vars]
                if daily_vars:
                    self.model.Add(sum(daily_vars) <= 1)

        # 2. Max consecutive duties
        limit = self.config.constraints.max_consecutive_duties
        for person in self.req.staff_ids:
            for i in range(len(self.days_range) - limit):
                window_days = self.days_range[i : i + limit + 1]
                window_vars = []
                for d in window_days:
                    for s in all_shifts:
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

                possible_prevs = [s for s in all_shifts if (person, day, s) in self.vars]
                possible_nexts = [s for s in all_shifts if (person, next_day, s) in self.vars]

                for prev_shift in possible_prevs:
                    for next_shift in possible_nexts:
                        # Use base type for rules (AM_2 -> PM_1 treated as AM -> PM)
                        prev_base = get_base_shift_type(prev_shift)
                        next_base = get_base_shift_type(next_shift)

                        status = rules.get(prev_base, {}).get(next_base, C.RuleStatus.ALLOWED.value)

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
        """
        Applies the optimization objective:
        1. Calculate points for each person.
        2. Minimize gap between busiest and least busy.
        3. Minimize Soft Bans.
        """
        person_points = []
        SCALE = C.SCORE_SCALE_FACTOR
        SOFT_BAN_WEIGHT = C.SOFT_BAN_PENALTY_MULTIPLIER * SCALE

        # --- Catch Up Limit Calculation (Relative) ---
        catch_up_limit = self.config.constraints.catch_up_limit
        max_allowed_points = 0

        if catch_up_limit > 0:
            total_roster_points = 0

            for (day, shift), weight in self.req.shift_weights.items():
                if day in self.req.inactive_days:
                    continue

                # Check if this shift actually requires manpower
                # shift_weights contains entries for AM, AM_2 etc.
                base_shift = get_base_shift_type(shift)

                # Determine how many people work THIS specific shift code (e.g. AM_2)
                # It is always the base requirement (e.g. 1)
                if base_shift == "S/B":
                    count = self.config.constraints.standby_per_day
                else:
                    count = self.config.constraints.personnel_needed_per_shift.get(base_shift, 0)

                # Filter inactive modes if necessary (logic copied from original)
                mode = self.req.day_modes.get(day, C.ScheduleMode.SHIFT.value)
                is_active = False
                if mode == C.ScheduleMode.FULL_24H.value:
                    if base_shift in ["24H", "S/B"]:
                        is_active = True
                else:
                    if base_shift in ["AM", "PM", "S/B"]:
                        is_active = True

                if is_active:
                    total_roster_points += weight * count

            num_staff = len(self.req.staff_ids)
            if num_staff > 0:
                avg_points = total_roster_points / num_staff
                raw_limit = int(avg_points + (catch_up_limit * SCALE))
                max_allowed_points = max(1, raw_limit)
            else:
                max_allowed_points = 0

        # --- End Catch Up Calculation ---

        # Define bounds for points using constants
        MIN_DOMAIN = C.SOLVER_MIN_POINTS_DOMAIN
        MAX_DOMAIN = C.SOLVER_MAX_POINTS_DOMAIN

        for person in self.req.staff_ids:
            expr = []
            for day in self.days_range:
                for shift in self._get_all_shift_keys():
                    if (person, day, shift) not in self.vars:
                        continue
                    weight = self.req.shift_weights.get((day, shift), 0)
                    if weight > 0:
                        expr.append(self.vars[(person, day, shift)] * weight)

            monthly_total = self.model.NewIntVar(0, MAX_DOMAIN, f"month_pts_{person}")
            self.model.Add(monthly_total == sum(expr))

            if catch_up_limit > 0 and max_allowed_points > 0:
                self.model.Add(monthly_total <= max_allowed_points)

            # Use MIN_DOMAIN to allow negative totals
            total_pts = self.model.NewIntVar(MIN_DOMAIN, MAX_DOMAIN, f"total_pts_{person}")
            carry_fwd = int(self.prev_balance.get(person, 0.0) * SCALE)
            self.model.Add(total_pts == carry_fwd + monthly_total)

            person_points.append(total_pts)

        if not person_points:
            return

        min_pts = self.model.NewIntVar(MIN_DOMAIN, MAX_DOMAIN, "min_points")
        max_pts = self.model.NewIntVar(MIN_DOMAIN, MAX_DOMAIN, "max_points")

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
        """
        Runs the CP-SAT solver on the built model.

        Returns:
            Optional[Tuple[Dict[Tuple[str, int], str], Any]]:
                A tuple of (schedule, status) if successful, where:
                - schedule: Dict mapping (person, day) to shift name
                - status: Solver status code (OPTIMAL or FEASIBLE)
                Returns None if solving fails.
        """
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

    def _get_all_shift_keys(self) -> List[str]:
        """Helper to return all currently active shift strings (AM, AM_2, S/B, etc)"""
        keys = []
        for t in range(1, self.active_teams + 1):
            keys.extend([get_shift_name(x, t) for x in ["AM", "PM", "24H"]])
        for t in range(1, self.sb_teams + 1):
            keys.append(get_shift_name("S/B", t))
        return keys
