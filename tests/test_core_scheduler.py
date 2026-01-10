"""
tests/test_core_scheduler.py

Unit tests for the DutySchedulerEngine's core logic.
Verifies specific constraint application and edge cases in isolation.
"""

import pytest

from app.core.scheduler import DutySchedulerEngine, SolverRequest
from app.models.config import AppConfig


@pytest.fixture
def scheduler_setup():
    """
    Fixture providing a basic scheduler setup.

    Returns:
        Tuple[AppConfig, SolverRequest]: Config and Request objects initialized for Jan 2025.
    """
    config = AppConfig.default()
    # Increase personnel to ensure feasibility with default constraints
    # Default constraints: 1 AM + 1 PM + 1 S/B = 3 people/day.
    # Rest rules (S/B -> Rest) mean we need roughly 2x-3x the daily requirement to rotate.
    config.personnel = ["A", "B", "C", "D", "E", "F", "G", "H"]

    # Simple month configuration (3 days)
    day_modes = {1: "SHIFT", 2: "SHIFT", 3: "SHIFT"}

    request = SolverRequest(
        staff_ids=config.personnel, year=2025, month=1, fixed_assignments={}, day_modes=day_modes, inactive_days=[]
    )
    return config, request


def test_scheduler_init(scheduler_setup):
    """Test that the scheduler initializes correctly with valid inputs."""
    config, request = scheduler_setup
    engine = DutySchedulerEngine(config, {}, request)
    assert engine.model is not None
    assert engine.vars == {}


def test_build_model_creates_vars(scheduler_setup):
    """Test that build_model populates the decision variables dictionary."""
    config, request = scheduler_setup
    engine = DutySchedulerEngine(config, {}, request)
    engine.build_model()

    # For 8 people, 3 days, "SHIFT" mode (AM, PM, S/B) -> 8*3*3 = 72 vars approx
    assert len(engine.vars) > 0
    # Check a specific key exists
    assert ("A", 1, "AM") in engine.vars


def test_solve_basic_feasible(scheduler_setup):
    """Test that the solver finds a solution for a trivial case."""
    config, request = scheduler_setup
    engine = DutySchedulerEngine(config, {}, request)
    engine.build_model()
    result = engine.solve()

    assert result is not None
    schedule, _ = result
    assert isinstance(schedule, dict)
    assert len(schedule) > 0
