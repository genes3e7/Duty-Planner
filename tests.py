"""
tests.py
Unit tests for the Duty Scheduler Logic Engine.
"""
import unittest
import constants as C
from scheduler_engine import DutySchedulerEngine

class TestDutyScheduler(unittest.TestCase):
    def setUp(self) -> None:
        self.config = C.DEFAULT_CONFIG_TEMPLATE.copy()
        self.config['personnel'] = ['A', 'B', 'C']
        self.config['constraints']['personnel_needed_per_shift'] = {'AM': 1, 'PM': 1, '24H': 1}
        self.prev = {'A': 0.0, 'B': 0.0, 'C': 0.0}
        self.leaves = []

    def test_basic_solve(self) -> None:
        engine = DutySchedulerEngine(self.config, self.prev, self.leaves)
        engine.build_model()
        res = engine.solve()
        self.assertIsNotNone(res)

    def test_impossible(self) -> None:
        # Everyone on leave same day
        self.leaves = [('A', 1), ('B', 1), ('C', 1)]
        engine = DutySchedulerEngine(self.config, self.prev, self.leaves)
        engine.build_model()
        res = engine.solve()
        self.assertIsNone(res)

if __name__ == '__main__':
    unittest.main()
