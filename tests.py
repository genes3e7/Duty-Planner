"""
tests.py

Unit tests for v8.0 Architecture.
"""
import unittest
from config_models import AppConfig
from scheduler_engine import DutySchedulerEngine, SolverRequest
from constants import ShiftType

class TestEngine(unittest.TestCase):
    def setUp(self):
        self.cfg = AppConfig.default()
        self.cfg.personnel = ['A','B','C','D','E','F']
        self.prev = {p:0.0 for p in self.cfg.personnel}
        # Default Request
        self.req = SolverRequest(
            staff_ids=self.cfg.personnel,
            year=2025, month=1,
            fixed_assignments={},
            day_modes={}, inactive_days=[]
        )

    def test_solve_basic(self):
        """Test basic solve capability."""
        eng = DutySchedulerEngine(self.cfg, self.prev, self.req)
        eng.build_model()
        res = eng.solve()
        self.assertIsNotNone(res)

    def test_inactive_days(self):
        """Test that inactive days get no assignments."""
        self.req.inactive_days = [1, 2]
        eng = DutySchedulerEngine(self.cfg, self.prev, self.req)
        eng.build_model()
        sched, _ = eng.solve()
        # Verify no keys exist for day 1 or 2
        for (p, d) in sched.keys():
            self.assertNotIn(d, [1, 2])

    def test_24h_mode(self):
        """Test that 24H mode forces only 24H shifts."""
        self.req.day_modes = {1: "24H"}
        eng = DutySchedulerEngine(self.cfg, self.prev, self.req)
        eng.build_model()
        sched, _ = eng.solve()
        
        # Check day 1
        day1 = [v for (k,v) in sched.items() if k[1] == 1]
        for s in day1:
            self.assertIn(s, [ShiftType.FULL_24H, ShiftType.STANDBY])

if __name__ == '__main__':
    unittest.main()
