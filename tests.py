"""
tests.py
Unit tests for Duty Scheduler Pro v6.0
"""
import unittest
import constants as C
from scheduler_engine import DutySchedulerEngine

class TestDutyScheduler(unittest.TestCase):
    def setUp(self) -> None:
        self.config = C.DEFAULT_CONFIG_TEMPLATE.copy()
        # Increased staff count to 8 to satisfy strict gap rule
        self.config['personnel'] = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'] 
        self.config['constraints']['personnel_needed_per_shift'] = {'AM': 1, 'PM': 1, '24H': 1}
        self.prev = {p: 0.0 for p in self.config['personnel']}
        self.leaves = []
        self.day_modes = {} 
        self.fixed = {}

    def test_basic_solve(self) -> None:
        """Test if a solution is found for a standard scenario."""
        engine = DutySchedulerEngine(self.config, self.prev, self.leaves, self.day_modes, self.fixed)
        engine.build_model()
        res = engine.solve()
        self.assertIsNotNone(res)

    def test_impossible(self) -> None:
        """Test if solver fails when everyone is forced on Leave."""
        self.fixed = {(p, 1): 'X' for p in self.config['personnel']}
        engine = DutySchedulerEngine(self.config, self.prev, self.leaves, self.day_modes, self.fixed)
        engine.build_model()
        res = engine.solve()
        self.assertIsNone(res)

if __name__ == '__main__':
    unittest.main()
