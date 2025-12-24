"""
tests.py

Unit tests for v3.0.0 Architecture using pytest.
"""

import pytest

from app.constants import ShiftType
from app.core.scheduler import DutySchedulerEngine, SolverRequest
from app.models.config import AppConfig


@pytest.fixture
def scheduler_data():
    """
    Fixture that provides a fresh setup (Config, Previous Balance, SolverRequest)
    for every single test function. Replaces the old 'setUp' method.
    """
    cfg = AppConfig.default()
    # Use a smaller subset of personnel for faster testing
    cfg.personnel = ["A", "B", "C", "D", "E", "F"]
    prev = {p: 0.0 for p in cfg.personnel}

    # Default Solver Request
    req = SolverRequest(
        staff_ids=cfg.personnel,
        year=2025,
        month=1,
        fixed_assignments={},
        day_modes={},
        inactive_days=[],
    )
    return cfg, prev, req


def test_solve_basic(scheduler_data):
    """Test basic solve capability to ensure the engine runs."""
    cfg, prev, req = scheduler_data
    eng = DutySchedulerEngine(cfg, prev, req)
    eng.build_model()
    res = eng.solve()

    # Assert a solution was found
    assert res is not None


def test_inactive_days(scheduler_data):
    """Test that days marked as 'inactive' receive ZERO assignments."""
    cfg, prev, req = scheduler_data
    req.inactive_days = [1, 2]  # Disable Day 1 and Day 2

    eng = DutySchedulerEngine(cfg, prev, req)
    eng.build_model()
    res = eng.solve()

    assert res is not None
    sched, _ = res

    # Iterate through the resulting schedule keys (person, day)
    # Ensure no assignment exists for days 1 or 2
    for p, d in sched.keys():
        assert d not in [1, 2]


def test_24h_mode(scheduler_data):
    """Test that days set to '24H' mode only assign 24H or Standby shifts."""
    cfg, prev, req = scheduler_data
    req.day_modes = {1: "24H"}  # Force Day 1 to 24H mode

    eng = DutySchedulerEngine(cfg, prev, req)
    eng.build_model()
    res = eng.solve()

    assert res is not None
    sched, _ = res

    # Extract all shifts assigned on Day 1
    day1_shifts = [v for (k, v) in sched.items() if k[1] == 1]

    # Valid types are ONLY 24H or STANDBY (no AM/PM allowed)
    valid_types = [ShiftType.FULL_24H, ShiftType.STANDBY]

    for s in day1_shifts:
        assert s in valid_types
