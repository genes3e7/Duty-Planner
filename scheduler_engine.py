"""
scheduler_engine.py

Core Logic: Constraint Satisfaction Problem (CSP) Solver.
Wraps Google OR-Tools to solve the rostering schedule.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import holidays
import pandas as pd
from ortools.sat.python import cp_model  # type: ignore

import constants as C
from config_models import AppConfig


@dataclass
class SolverRequest:
    """
    Data Transfer Object to pass raw data to the solver.
    """

    staff_ids: List[str]
    year: int
    month: int
    fixed_assignments: Dict[Tuple[str, int], str]
    day_modes: Dict[int, str]
    inactive_days: List[int]


class DutySchedulerEngine:
    """The Engine class wrapping the CP-SAT solver."""

    def __init__(
        self, config: AppConfig, prev_balance: Dict[str, float], request: SolverRequest
    ) -> None:
        """
        Args:
            config: Application rules/constraints.
            prev_balance: Points brought forward.
            request: Current solver request data.
        """
        self.cfg = config
        self.prev = prev_balance
        self.req = request

        # Calculate days in month
        try:
            self.num_days = pd.Period(f"{self.req.year}-{self.req.month}").days_in_month
        except Exception:
            self.num_days = 30

        self.sg_holidays = holidays.SG(years=self.req.year)
        self.model = cp_model.CpModel()
        self.shifts = {}

    def _is_ph_or_weekend(self, day: int) -> Tuple[bool, bool]:
        """Checks if a day is a Public Holiday or Weekend."""
        try:
            dt = pd.Timestamp(year=self.req.year, month=self.req.month, day=day)
            return (dt in self.sg_holidays, dt.dayofweek >= 5)
        except Exception:
            return (False, False)

    def build_model(self) -> None:
        """Constructs variables and constraints."""
        logging.info("Building CSP Model...")

        # 1. Variables
        for p in self.req.staff_ids:
            for d in range(1, self.num_days + 1):
                for s in C.ACTIVE_DUTIES:
                    self.shifts[(p, d, s)] = self.model.NewBoolVar(f"s_{p}_{d}_{s}")

        # 2. Fixed Assignments
        for (p, d), val in self.req.fixed_assignments.items():
            if d in self.req.inactive_days:
                continue
            if val == C.ShiftType.LEAVE:
                self.model.Add(
                    sum(self.shifts[(p, d, s)] for s in C.ACTIVE_DUTIES) == 0
                )
            elif val in C.ACTIVE_DUTIES:
                self.model.Add(self.shifts[(p, d, val)] == 1)

        # 3. Manpower Constraints
        c_reqs = self.cfg.constraints.personnel_needed_per_shift

        for d in range(1, self.num_days + 1):
            if d in self.req.inactive_days:
                # Force zero on inactive days
                for p in self.req.staff_ids:
                    self.model.Add(
                        sum(self.shifts[(p, d, s)] for s in C.ACTIVE_DUTIES) == 0
                    )
                continue

            mode = self.req.day_modes.get(d, C.ScheduleMode.SHIFT)

            if mode == C.ScheduleMode.FULL_24H:
                target_24 = c_reqs.get(C.ShiftType.FULL_24H.value, 1)
                self.model.Add(
                    sum(
                        self.shifts[(p, d, C.ShiftType.FULL_24H)]
                        for p in self.req.staff_ids
                    )
                    == target_24
                )
                # Ensure no AM/PM
                self.model.Add(
                    sum(self.shifts[(p, d, C.ShiftType.AM)] for p in self.req.staff_ids)
                    == 0
                )
                self.model.Add(
                    sum(self.shifts[(p, d, C.ShiftType.PM)] for p in self.req.staff_ids)
                    == 0
                )
            else:
                t_am = c_reqs.get(C.ShiftType.AM.value, 1)
                t_pm = c_reqs.get(C.ShiftType.PM.value, 1)
                self.model.Add(
                    sum(self.shifts[(p, d, C.ShiftType.AM)] for p in self.req.staff_ids)
                    == t_am
                )
                self.model.Add(
                    sum(self.shifts[(p, d, C.ShiftType.PM)] for p in self.req.staff_ids)
                    == t_pm
                )
                self.model.Add(
                    sum(
                        self.shifts[(p, d, C.ShiftType.FULL_24H)]
                        for p in self.req.staff_ids
                    )
                    == 0
                )

            # Standby always needed
            self.model.Add(
                sum(
                    self.shifts[(p, d, C.ShiftType.STANDBY)] for p in self.req.staff_ids
                )
                == self.cfg.constraints.standby_per_day
            )

        # 4. Strict Gap Rule
        for p in self.req.staff_ids:
            # Exclusivity
            for d in range(1, self.num_days + 1):
                self.model.Add(
                    sum(self.shifts[(p, d, s)] for s in C.ACTIVE_DUTIES) <= 1
                )
            # No consecutive days
            for d in range(1, self.num_days):
                work_today = sum(self.shifts[(p, d, s)] for s in C.ACTIVE_DUTIES)
                work_tmrw = sum(self.shifts[(p, d + 1, s)] for s in C.ACTIVE_DUTIES)
                self.model.Add(work_today + work_tmrw <= 1)

    def solve(self) -> Optional[Tuple[Dict, List]]:
        """Executes the solver."""
        person_scores = []
        SCALE = C.SCORE_SCALE_FACTOR

        for p in self.req.staff_ids:
            score_expr = []
            start_bal = int(self.prev.get(p, 0.0) * SCALE)

            for d in range(1, self.num_days + 1):
                if d in self.req.inactive_days:
                    continue
                is_ph, is_wknd = self._is_ph_or_weekend(d)

                mult = 1.0
                if is_ph:
                    mult = self.cfg.points.ph_multiplier
                elif is_wknd:
                    mult = self.cfg.points.weekend_multiplier

                for s in C.ACTIVE_DUTIES:
                    base = self.cfg.points.get_by_type(s)
                    pts = int(base * mult * SCALE)
                    if pts > 0:
                        score_expr.append(self.shifts[(p, d, s)] * pts)

            total = self.model.NewIntVar(-1000000, 1000000, f"t_{p}")
            self.model.Add(total == sum(score_expr) + start_bal)
            person_scores.append(total)

        # Minimize Variance
        min_s = self.model.NewIntVar(-1000000, 1000000, "min")
        max_s = self.model.NewIntVar(-1000000, 1000000, "max")
        self.model.AddMinEquality(min_s, person_scores)
        self.model.AddMaxEquality(max_s, person_scores)

        self.model.Minimize((max_s - min_s))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 15.0
        status = solver.Solve(self.model)

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            sched = {}
            for p in self.req.staff_ids:
                for d in range(1, self.num_days + 1):
                    for s in C.ACTIVE_DUTIES:
                        if solver.Value(self.shifts[(p, d, s)]):
                            sched[(p, d)] = s

            summary = []
            for i, p in enumerate(self.req.staff_ids):
                final = solver.Value(person_scores[i])
                start = self.prev.get(p, 0.0)
                summary.append(
                    {
                        "Name": p,
                        "Brought Fwd": start,
                        "Month Pts": (final / SCALE) - start,
                        "Carry Over": final / SCALE,
                    }
                )
            return sched, summary
        return None
