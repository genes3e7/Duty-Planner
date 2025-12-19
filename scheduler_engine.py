"""
scheduler_engine.py

Core Logic: Constraint Satisfaction Problem (CSP) Solver using Google OR-Tools.
Enforces strict rules: Manpower, Exclusivity, and Resting gaps.
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
import holidays
import pandas as pd
from ortools.sat.python import cp_model # type: ignore
import constants as C

class DutySchedulerEngine:
    def __init__(
        self,
        config: Dict[str, Any],
        prev_balance: Dict[str, float],
        leaves: List[Tuple[str, int]],   
        day_modes: Dict[int, str],       
        fixed_assignments: Dict[Tuple[str, int], str]
    ) -> None:
        self.cfg = config
        self.personnel = config.get('personnel', [])
        self.prev_balance = prev_balance
        self.leaves = leaves
        self.day_modes = day_modes
        self.fixed_assignments = fixed_assignments 
        
        # Date Logic
        self.year = int(config.get('year', 2025))
        self.month = int(config.get('month', 1))
        
        try:
            self.num_days = pd.Period(f'{self.year}-{self.month}').days_in_month
        except Exception:
            self.num_days = 30 
            
        self.sg_holidays = holidays.SG(years=self.year)
        
        self.model = cp_model.CpModel()
        self.shifts: Dict[Tuple[str, int, str], cp_model.IntVar] = {}
        self.shift_types = C.SHIFT_TYPES

    def _is_ph_or_weekend(self, day: int) -> Tuple[bool, bool]:
        """Determines if a day is a Public Holiday or Weekend."""
        try:
            date = pd.Timestamp(year=self.year, month=self.month, day=day)
            is_ph = date in self.sg_holidays
            is_wknd = date.dayofweek >= 5
            return bool(is_ph), bool(is_wknd)
        except Exception:
            return False, False

    def build_model(self) -> None:
        """Constructs the constraint model."""
        logging.info("Building CSP Model...")

        # 1. Variables
        for p in self.personnel:
            for d in range(1, self.num_days + 1):
                for s in self.shift_types:
                    self.shifts[(p, d, s)] = self.model.NewBoolVar(f'shift_{p}_{d}_{s}')

        # 2. Fixed Assignments
        for (p, d), shift_type in self.fixed_assignments.items():
            if shift_type == "X":
                self.model.Add(sum(self.shifts[(p, d, s)] for s in self.shift_types) == 0)
            elif shift_type in self.shift_types:
                self.model.Add(self.shifts[(p, d, shift_type)] == 1)

        # 3. Manpower Constraints
        reqs = self.cfg.get('constraints', {}).get('personnel_needed_per_shift', {})
        sb_req = int(self.cfg.get('constraints', {}).get('standby_per_day', 1))
        
        for d in range(1, self.num_days + 1):
            mode = self.day_modes.get(d, "Shift") 
            t_am = t_pm = t_24 = 0
            
            if mode == "24H":
                t_24 = int(reqs.get('24H', 1))
            else: 
                t_am = int(reqs.get('AM', 1))
                t_pm = int(reqs.get('PM', 1))

            self.model.Add(sum(self.shifts[(p, d, 'AM')] for p in self.personnel) == t_am)
            self.model.Add(sum(self.shifts[(p, d, 'PM')] for p in self.personnel) == t_pm)
            self.model.Add(sum(self.shifts[(p, d, '24H')] for p in self.personnel) == t_24)
            self.model.Add(sum(self.shifts[(p, d, 'S/B')] for p in self.personnel) == sb_req)

        # 4. Strict Gap Rule (No Consecutive Duty)
        for p in self.personnel:
            # Max 1 shift per day
            for d in range(1, self.num_days + 1):
                self.model.Add(sum(self.shifts[(p, d, s)] for s in self.shift_types) <= 1)

            # No back-to-back days
            for d in range(1, self.num_days):
                working_today = sum(self.shifts[(p, d, s)] for s in self.shift_types)
                working_tmrw = sum(self.shifts[(p, d+1, s)] for s in self.shift_types)
                self.model.Add(working_today + working_tmrw <= 1)

    def solve(self) -> Optional[Tuple[Dict[Tuple[str, int], str], List[Dict[str, Any]]]]:
        """Executes the solver."""
        logging.info("Solving...")
        person_scores = []
        SCALE = C.SCORE_SCALE_FACTOR 
        
        for p in self.personnel:
            score_expr = []
            start_bal = int(self.prev_balance.get(p, 0.0) * SCALE)
            
            for d in range(1, self.num_days + 1):
                is_ph, is_wknd = self._is_ph_or_weekend(d)
                mult = 1.0
                if is_ph: mult = float(self.cfg['points'].get('ph_multiplier', 1.0))
                elif is_wknd: mult = float(self.cfg['points'].get('weekend_multiplier', 1.0))
                
                for s in self.shift_types:
                    base = float(self.cfg['points'].get(s, 0.0))
                    pts = int(base * mult * SCALE)
                    if pts > 0:
                        score_expr.append(self.shifts[(p, d, s)] * pts)
            
            total = self.model.NewIntVar(-1000000, 1000000, f'total_{p}')
            self.model.Add(total == sum(score_expr) + start_bal)
            person_scores.append(total)

        # Objective: Balance scores and equal distribution of Standby
        min_s = self.model.NewIntVar(-1000000, 1000000, 'min_s')
        max_s = self.model.NewIntVar(-1000000, 1000000, 'max_s')
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

        # Weighted Objective
        self.model.Minimize(
            (max_s - min_s) * C.WEIGHT_POINTS_BALANCE + 
            (max_sb - min_sb) * C.WEIGHT_STANDBY_BALANCE
        )

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 15.0 
        status = solver.Solve(self.model)
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return self._format_results(solver, person_scores, SCALE)
        else:
            logging.warning("No solution found.")
            return None

    def _format_results(self, solver, person_scores, scale):
        schedule = {}
        for p in self.personnel:
            for d in range(1, self.num_days + 1):
                for s in self.shift_types:
                    if solver.Value(self.shifts[(p, d, s)]):
                        schedule[(p, d)] = s
        summary = []
        for i, p in enumerate(self.personnel):
            final_score = solver.Value(person_scores[i])
            start_bal = self.prev_balance.get(p, 0.0)
            month_pts = (final_score / scale) - start_bal
            summary.append({
                'Name': p, 
                'Brought Fwd': start_bal, 
                'Month Pts': month_pts, 
                'Carry Over': final_score / scale
            })
        return schedule, summary
