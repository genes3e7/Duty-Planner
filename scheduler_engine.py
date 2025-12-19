"""
scheduler_engine.py

The Logic Core. Translates user constraints into a mathematical model
using Google OR-Tools (Constraint Satisfaction Problem).
"""

import logging
from typing import Dict, List, Tuple, Optional, Any, Union

import holidays
import pandas as pd
from ortools.sat.python import cp_model  # type: ignore

import constants as C


class DutySchedulerEngine:
    """Solves the rostering problem using constraint programming."""

    def __init__(
        self,
        config: Dict[str, Any],
        prev_balance: Dict[str, float],
        leaves: List[Tuple[str, int]]
    ) -> None:
        self.cfg = config
        self.personnel: List[str] = config.get('personnel', [])
        
        logging.info(f"Initializing Scheduler for {len(self.personnel)} staff.")

        if not self.personnel:
            raise ValueError("Personnel list is empty. Please add staff in Settings.")

        try:
            self.year: int = int(config.get('year', 0))
            self.month: int = int(config.get('month', 0))
            if not (1 <= self.month <= 12):
                raise ValueError("Month must be 1-12")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid Date Configuration: {e}")

        self.prev_balance = prev_balance
        self.leaves = leaves

        try:
            self.num_days: int = pd.Period(f'{self.year}-{self.month}').days_in_month
        except Exception as e:
            raise ValueError(f"Date calculation error: {e}")

        self.sg_holidays: Any = holidays.SG(years=self.year)
        self.model = cp_model.CpModel()
        self.shifts: Dict[Tuple[str, int, str], cp_model.IntVar] = {}
        self.shift_types: List[str] = C.SHIFT_TYPES

    def _is_ph_or_weekend(self, day: int) -> Tuple[bool, bool]:
        """Returns (is_public_holiday, is_weekend)."""
        date = pd.Timestamp(year=self.year, month=self.month, day=day)
        is_ph = date in self.sg_holidays
        is_wknd = date.dayofweek >= 5
        return bool(is_ph), bool(is_wknd)

    def build_model(self) -> None:
        """Constructs variables and constraints for the solver."""
        logging.info("Building CSP Model...")

        # 1. Decision Variables
        for p in self.personnel:
            for d in range(1, self.num_days + 1):
                for s in self.shift_types:
                    self.shifts[(p, d, s)] = self.model.NewBoolVar(f'shift_{p}_{d}_{s}')

        # 2. Daily Constraints
        for d in range(1, self.num_days + 1):
            is_ph, is_wknd = self._is_ph_or_weekend(d)
            mode: str = self.cfg.get('mode', 'shift')

            try:
                reqs: Dict[str, Any] = self.cfg['constraints']['personnel_needed_per_shift']
                r_am = int(reqs.get('AM', 1))
                r_pm = int(reqs.get('PM', 1))
                r_24 = int(reqs.get('24H', 1))
            except (KeyError, ValueError, TypeError):
                raise ValueError("Invalid 'personnel_needed_per_shift' settings.")

            target_am = target_pm = target_24 = 0

            # Logic: Mode Selection
            if mode == '24h':
                target_24 = r_24
            elif mode == 'shift':
                target_am = r_am
                target_pm = r_pm
            elif mode == 'hybrid':
                if is_ph or is_wknd:
                    target_24 = r_24
                else:
                    target_am = r_am
                    target_pm = r_pm

            self.model.Add(sum(self.shifts[(p, d, 'AM')] for p in self.personnel) == target_am)
            self.model.Add(sum(self.shifts[(p, d, 'PM')] for p in self.personnel) == target_pm)
            self.model.Add(sum(self.shifts[(p, d, '24H')] for p in self.personnel) == target_24)

            sb_req = int(self.cfg['constraints'].get('standby_per_day', 1))
            self.model.Add(sum(self.shifts[(p, d, 'S/B')] for p in self.personnel) == sb_req)

        # 3. Personnel Constraints
        min_rest = int(self.cfg['constraints'].get('min_rest_after_24h', 1))

        for p in self.personnel:
            for d in range(1, self.num_days + 1):
                # Max 1 shift per day
                self.model.Add(sum(self.shifts[(p, d, s)] for s in self.shift_types) <= 1)

                # Leave constraint
                if (p, d) in self.leaves:
                    self.model.Add(sum(self.shifts[(p, d, s)] for s in self.shift_types) == 0)

            # Rest after 24H
            for d in range(1, self.num_days - min_rest + 1):
                self.model.Add(
                    sum(sum(self.shifts[(p, d+r, s)] for s in self.shift_types)
                        for r in range(1, min_rest+1)) == 0
                ).OnlyEnforceIf(self.shifts[(p, d, '24H')])

    def solve(self) -> Optional[Tuple[Dict[Tuple[str, int], str], List[Dict[str, Union[str, float]]]]]:
        """Executes the solver."""
        logging.info("Solving model...")
        person_scores: List[cp_model.IntVar] = []
        SCALE = C.SCORE_SCALE_FACTOR

        for p in self.personnel:
            score_expr = []
            start_bal = int(self.prev_balance.get(p, 0.0) * SCALE)

            for d in range(1, self.num_days + 1):
                is_ph, is_wknd = self._is_ph_or_weekend(d)
                
                mult = 1.0
                if is_ph:
                    mult = float(self.cfg['points']['ph_multiplier'])
                elif is_wknd:
                    mult = float(self.cfg['points']['weekend_multiplier'])

                for s in self.shift_types:
                    base = float(self.cfg['points'].get(s, 0))
                    pts = int(base * mult * SCALE)
                    if pts > 0:
                        score_expr.append(self.shifts[(p, d, s)] * pts)

            total = self.model.NewIntVar(-100000, 100000, f'total_{p}')
            self.model.Add(total == sum(score_expr) + start_bal)
            person_scores.append(total)

        # Objectives: Minimize spread of points and standby duties
        min_s = self.model.NewIntVar(-100000, 100000, 'min_s')
        max_s = self.model.NewIntVar(-100000, 100000, 'max_s')
        self.model.AddMinEquality(min_s, person_scores)
        self.model.AddMaxEquality(max_s, person_scores)

        sb_counts = []
        for p in self.personnel:
            count = sum(self.shifts[(p, d, 'S/B')] for d in range(1, self.num_days+1))
            sb_counts.append(count)

        min_sb = self.model.NewIntVar(0, 31, 'min_sb')
        max_sb = self.model.NewIntVar(0, 31, 'max_sb')
        self.model.AddMinEquality(min_sb, sb_counts)
        self.model.AddMaxEquality(max_sb, sb_counts)

        # Weighted Minimization
        self.model.Minimize(
            (max_s - min_s) * C.WEIGHT_POINTS_BALANCE +
            (max_sb - min_sb) * C.WEIGHT_STANDBY_BALANCE
        )

        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            logging.info(f"Solution Found. Status: {solver.StatusName(status)}")
            return self._format_results(solver, person_scores, SCALE)
        else:
            logging.warning("No solution found.")
            return None

    def _format_results(
        self,
        solver: cp_model.CpSolver,
        person_scores: List[cp_model.IntVar],
        scale: int
    ) -> Tuple[Dict[Tuple[str, int], str], List[Dict[str, Union[str, float]]]]:
        schedule: Dict[Tuple[str, int], str] = {}
        for p in self.personnel:
            for d in range(1, self.num_days + 1):
                for s in self.shift_types:
                    if solver.Value(self.shifts[(p, d, s)]):
                        schedule[(p, d)] = s
        
        summary: List[Dict[str, Union[str, float]]] = []
        for i, p in enumerate(self.personnel):
            final_score_scaled = solver.Value(person_scores[i])
            start_bal = self.prev_balance.get(p, 0.0)
            month_pts = (final_score_scaled / scale) - start_bal
            
            summary.append({
                'Name': p,
                'Brought Fwd': start_bal,
                'Month Pts': month_pts,
                'Carry Over': final_score_scaled / scale
            })
            
        return schedule, summary
