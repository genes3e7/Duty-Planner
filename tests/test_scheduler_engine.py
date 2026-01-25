"""
tests/test_scheduler_engine.py

Focus: Core mechanics of the DutySchedulerEngine.
Verifies that the solver initializes correctly, creates variables, and handles
fundamental feasibility (Optimal, Infeasible, Empty).
"""

import pytest
from ortools.sat.python import cp_model

from app.constants import ScheduleMode
from app.core.scheduler import DutySchedulerEngine, SolverRequest
from app.models.config import AppConfig

# --- Fixtures ---


@pytest.fixture
def basic_engine_setup():
    """
    Returns a config and request ready for engine initialization.
    NOTE: Default config requires 3 people/day (1 AM, 1 PM, 1 SB).
    We provide 4 staff to ensure feasibility.
    """
    config = AppConfig.default()
    config.personnel = ["A", "B", "C", "D"]
    # 2-day month
    day_modes = {1: ScheduleMode.SHIFT.value, 2: ScheduleMode.SHIFT.value}
    req = SolverRequest(
        staff_ids=config.personnel,
        year=2025,
        month=1,
        fixed_assignments={},
        day_modes=day_modes,
        inactive_days=[],
        shift_weights={},
    )
    return config, req


# --- Variable Creation Tests ---


def test_variable_creation(basic_engine_setup):
    """Test that solver variables are created for all staff/days/shifts."""
    config, req = basic_engine_setup
    engine = DutySchedulerEngine(config, {}, req)
    engine.build_model()

    # Verify standard shifts exist
    assert ("A", 1, "AM") in engine.vars
    assert ("B", 2, "PM") in engine.vars
    assert ("A", 1, "S/B") in engine.vars


def test_variable_creation_multi_team():
    """Test that variables for Team 2 are created if configured."""
    config = AppConfig.default()
    config.personnel = ["A"]
    config.constraints.num_active_teams = 2

    req = SolverRequest(
        staff_ids=["A"],
        year=2025,
        month=1,
        fixed_assignments={},
        day_modes={1: "SHIFT"},
        inactive_days=[],
        shift_weights={},
    )

    engine = DutySchedulerEngine(config, {}, req)
    engine.build_model()

    assert ("A", 1, "AM") in engine.vars
    assert ("A", 1, "AM_2") in engine.vars  # Team 2 variable


# --- Solvability Tests ---


def test_solve_basic_feasible(basic_engine_setup):
    """Test that the solver finds a solution for a trivial case."""
    config, req = basic_engine_setup
    engine = DutySchedulerEngine(config, {}, req)
    engine.build_model()

    result = engine.solve()
    assert result is not None
    schedule, status = result
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert len(schedule) > 0


def test_solver_empty_staff(basic_engine_setup):
    """Test defensive handling of empty staff list."""
    config, req = basic_engine_setup
    req.staff_ids = []  # Empty

    engine = DutySchedulerEngine(config, {}, req)
    engine.build_model()
    result = engine.solve()

    # Should return empty schedule, not crash
    assert result is not None
    schedule, _ = result
    assert schedule == {}


def test_solver_impossible_constraints(basic_engine_setup):
    """Test that solver returns None when constraints cannot be met."""
    config, req = basic_engine_setup
    # Impossible: Need 10 people per AM shift, but only have 4 staff
    config.constraints.personnel_needed_per_shift["AM"] = 10

    engine = DutySchedulerEngine(config, {}, req)
    engine.build_model()
    result = engine.solve()

    assert result is None


def test_solver_fixed_assignment_respect(basic_engine_setup):
    """Test that fixed 'X' assignments are respected."""
    config, req = basic_engine_setup
    req.fixed_assignments = {("A", 1): "X"}

    engine = DutySchedulerEngine(config, {}, req)
    engine.build_model()
    result = engine.solve()

    assert result is not None
    schedule, _ = result
    # A should NOT be assigned anything on Day 1
    assert ("A", 1) not in schedule


def test_solver_produces_schedule_with_holiday(basic_engine_setup):
    """
    Tests that the solver can handle a month with holidays (June 2025)
    and produces a schedule.
    """
    cfg, req = basic_engine_setup
    # June 2025 has 30 days
    req.year = 2025
    req.month = 6
    req.day_modes = {d: ScheduleMode.SHIFT.value for d in range(1, 31)}

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    res = engine.solve()

    assert res is not None
    schedule, _ = res
    assert len(schedule) > 0
