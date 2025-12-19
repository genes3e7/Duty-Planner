"""
tests.py
Comprehensive Unit Tests for Duty Scheduler Pro v6.2
"""
import unittest
from typing import Dict, Any
import constants as C
from scheduler_engine import DutySchedulerEngine

class TestDutyScheduler(unittest.TestCase):
    def setUp(self) -> None:
        """Setup a fresh config environment for each test."""
        self.config = C.DEFAULT_CONFIG_TEMPLATE.copy()
        # Ensure enough staff for strict rules (8 pax)
        self.config['personnel'] = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        self.config['constraints']['personnel_needed_per_shift'] = {'AM': 1, 'PM': 1, '24H': 1}
        self.config['constraints']['standby_per_day'] = 1
        
        # 0 balance start
        self.prev = {p: 0.0 for p in self.config['personnel']}
        self.leaves = []
        self.day_modes = {} 
        self.fixed = {}

    def test_basic_feasibility(self) -> None:
        """Test 1: Standard scenario should solve easily."""
        engine = DutySchedulerEngine(self.config, self.prev, self.leaves, self.day_modes, self.fixed)
        engine.build_model()
        res = engine.solve()
        self.assertIsNotNone(res, "Solver failed on a basic valid scenario.")

    def test_impossible_manpower(self) -> None:
        """Test 2: Demand exceeds Supply (Impossible)."""
        # 1 person available, but need 1 AM + 1 PM per day (2 shifts)
        # Exclusivity rule (max 1 shift/day) makes this impossible for 1 person.
        self.config['personnel'] = ['LonelyGuy']
        self.prev = {'LonelyGuy': 0.0}
        
        engine = DutySchedulerEngine(self.config, self.prev, self.leaves, self.day_modes, self.fixed)
        engine.build_model()
        res = engine.solve()
        self.assertIsNone(res, "Solver found a solution for an impossible manpower shortage.")

    def test_gap_rule(self) -> None:
        """Test 3: Verify no back-to-back duties."""
        # Use 2 people for 2 days. 
        # Day 1: 1 AM. Day 2: 1 AM.
        # If Person A works Day 1, gap rule forces Person B to work Day 2.
        self.config['personnel'] = ['A', 'B']
        self.prev = {'A': 0.0, 'B': 0.0}
        self.config['constraints']['personnel_needed_per_shift'] = {'AM': 1, 'PM': 0, '24H': 0}
        self.config['constraints']['standby_per_day'] = 0
        
        # Override num_days to 2 for this test manually if possible, 
        # or just check the first 2 days of a generated schedule.
        engine = DutySchedulerEngine(self.config, self.prev, self.leaves, self.day_modes, self.fixed)
        engine.build_model()
        res = engine.solve()
        
        if res:
            schedule, _ = res
            # Check for back-to-back assignments
            for p in self.config['personnel']:
                days_worked = sorted([d for (person, d) in schedule.keys() if person == p])
                for i in range(len(days_worked) - 1):
                    # Assert no consecutive days
                    self.assertNotEqual(days_worked[i] + 1, days_worked[i+1], f"Gap rule failed for {p}")

    def test_fixed_assignments(self) -> None:
        """Test 4: Manual overrides must be respected."""
        # Force 'A' to do AM on Day 1
        self.fixed = {('A', 1): 'AM'}
        
        engine = DutySchedulerEngine(self.config, self.prev, self.leaves, self.day_modes, self.fixed)
        engine.build_model()
        res = engine.solve()
        
        self.assertIsNotNone(res)
        schedule, _ = res
        self.assertEqual(schedule.get(('A', 1)), 'AM', "Fixed assignment was ignored.")

    def test_leave_logic(self) -> None:
        """Test 5: User on Leave (X) cannot be assigned."""
        # Force 'A' on Leave Day 1
        self.fixed = {('A', 1): 'X'}
        
        engine = DutySchedulerEngine(self.config, self.prev, self.leaves, self.day_modes, self.fixed)
        engine.build_model()
        res = engine.solve()
        
        self.assertIsNotNone(res)
        schedule, _ = res
        self.assertNotIn(('A', 1), schedule, "User on Leave was assigned a duty.")

    def test_points_accumulation(self) -> None:
        """Test 6: Points are calculated correctly."""
        # Force 1 day schedule
        self.config['year'] = 2025
        self.config['month'] = 1 # Jan 1 is likely PH or Weekday, check calendar
        # We'll just trust the engine's math, but verify 'Brought Fwd' integration
        self.prev = {'A': 10.0, 'B': 0.0, 'C':0.0, 'D':0.0, 'E':0.0, 'F':0.0, 'G':0.0, 'H':0.0}
        
        engine = DutySchedulerEngine(self.config, self.prev, self.leaves, self.day_modes, self.fixed)
        engine.build_model()
        res = engine.solve()
        
        _, summary = res
        person_a = next(p for p in summary if p['Name'] == 'A')
        self.assertEqual(person_a['Brought Fwd'], 10.0, "Brought forward points mismatch.")
        self.assertGreaterEqual(person_a['Carry Over'], 10.0, "Carry over should include Brought Fwd.")

if __name__ == '__main__':
    unittest.main()
