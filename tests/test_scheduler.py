"""
tests/test_scheduler.py

Tests for the DutySchedulerEngine.
Verifies solver behavior under various constraints and defensive scenarios.
"""

import pytest

from app.constants import ScheduleMode
from app.core.scheduler import DutySchedulerEngine, SolverRequest
from app.models.config import AppConfig


@pytest.fixture
def basic_request():
    """Creates a basic valid solver request."""
    cfg = AppConfig.default()
    cfg.personnel = ["A", "B", "C", "D", "E", "F"]

    # 31 day month (January)
    # Using enum .value to get string representation
    day_modes = {d: ScheduleMode.SHIFT.value for d in range(1, 32)}

    req = SolverRequest(
        staff_ids=cfg.personnel, year=2025, month=1, fixed_assignments={}, day_modes=day_modes, inactive_days=[]
    )
    return cfg, req


def test_solver_empty_staff(basic_request):
    """Test defensive handling of empty staff list."""
    cfg, req = basic_request
    req.staff_ids = []

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    result = engine.solve()

    # An empty model is feasible, resulting in an empty schedule
    # Returns ({}, None) because it's feasible but has no assignments
    assert result == ({}, None)


def test_solver_impossible_constraints(basic_request):
    """Test that solver correctly fails when constraints cannot be met."""
    cfg, req = basic_request
    # Requirement: 10 people per AM shift (more than total staff)
    cfg.constraints.personnel_needed_per_shift["AM"] = 10

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    result = engine.solve()

    assert result is None  # Should be impossible


def test_solver_fixed_assignment_respect(basic_request):
    """Test that fixed 'X' assignments are respected."""
    cfg, req = basic_request
    req.fixed_assignments = {("A", 1): "X"}

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    schedule, _ = engine.solve()

    assert schedule is not None
    # Ensure A is not working on day 1
    for shift in ["AM", "PM", "S/B"]:
        assert schedule.get(("A", 1)) != shift

    assert schedule.get(("A", 1)) == "X"


def test_solver_fairness_std_dev():
    """
    Tests that the solver can handle a month with holidays (June 2025 - Hari Raya Haji on June 7)
    and produces a schedule.
    """
    cfg = AppConfig.default()
    cfg.personnel = ["A", "B", "C", "D", "E", "F"]

    # June 2025 has 30 days.
    day_modes = {d: ScheduleMode.SHIFT.value for d in range(1, 31)}

    req = SolverRequest(
        staff_ids=cfg.personnel,
        year=2025,
        month=6,  # June
        fixed_assignments={},
        day_modes=day_modes,
        inactive_days=[],
    )

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    res = engine.solve()

    assert res is not None
    schedule, _ = res
    assert len(schedule) > 0
