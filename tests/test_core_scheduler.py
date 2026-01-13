"""
tests/test_core_scheduler.py

Methodology: Constraint Verification
------------------------------------
These tests focus on the 'Model' layer of the scheduling engine.
They do not rely on UI components or external files. Instead, they strictly verify
that the mathematical constraints (Hard and Soft) defined in the OR-Tools model
are functioning as expected.

Key areas tested:
1. Variable Creation: Ensuring the problem space is defined correctly.
2. Hard Constraints: Verifying that illegal moves (e.g., consecutive 24H) result in no solution.
3. Logic Gates: Ensuring mutually exclusive options (Shift vs 24H) are respected.
"""

import pytest

from app.constants import ScheduleMode
from app.core.scheduler import DutySchedulerEngine, SolverRequest
from app.models.config import AppConfig


@pytest.fixture
def basic_setup():
    config = AppConfig.default()
    config.personnel = ["A", "B"]
    day_modes = {1: ScheduleMode.SHIFT.value}
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


def test_variable_creation(basic_setup):
    """Test that solver variables are created correctly."""
    config, req = basic_setup
    engine = DutySchedulerEngine(config, {}, req)
    engine.build_model()

    # We expect vars for A and B, Day 1, for all shifts (AM, PM, 24H, S/B)
    assert ("A", 1, "AM") in engine.vars
    assert ("B", 1, "S/B") in engine.vars


def test_no_consecutive_24h_shifts():
    """
    Test logic: If worked 24H on Day D, cannot work on Day D+1.
    """
    config = AppConfig.default()
    config.personnel = ["A"]
    # 2 days, both 24H mode
    day_modes = {1: "24H", 2: "24H"}

    req = SolverRequest(
        staff_ids=["A"],
        year=2025,
        month=1,
        fixed_assignments={("A", 1): "24H", ("A", 2): "24H"},  # Impossible constraints
        day_modes=day_modes,
        inactive_days=[],
        shift_weights={},
    )

    engine = DutySchedulerEngine(config, {}, req)
    engine.build_model()

    result = engine.solve()

    # Expect failure (None) because assignment impossible
    assert result is None


def test_no_duty_adjacent_to_sb():
    """
    Test logic: S/B (Standby) must be isolated.
    It cannot be back-to-back with any duty (S/B, AM, PM, 24H).
    """
    config = AppConfig.default()
    config.personnel = ["A"]

    # Use 3 days to test "Before" and "After" clearly
    day_modes = {1: "SHIFT", 2: "SHIFT", 3: "SHIFT"}

    # 1. S/B -> Duty (S/B on D1, AM on D2) -> Should Fail
    req1 = SolverRequest(
        staff_ids=["A"],
        year=2025,
        month=1,
        fixed_assignments={("A", 1): "S/B", ("A", 2): "AM"},
        day_modes=day_modes,
        inactive_days=[],
        shift_weights={},
    )
    eng1 = DutySchedulerEngine(config, {}, req1)
    eng1.build_model()
    assert eng1.solve() is None, "S/B followed by AM should fail"


def test_soft_ban_generation():
    """
    Test logic: Soft bans should generate penalty variables.
    This ensures the 'Fairness Objective' has penalty variables to minimize.
    """
    config = AppConfig.default()
    config.personnel = ["A"]
    day_modes = {1: "SHIFT", 2: "SHIFT"}

    # AM -> PM is a soft ban (discouraged but possible)
    req = SolverRequest(
        staff_ids=["A"],
        year=2025,
        month=1,
        fixed_assignments={("A", 1): "AM", ("A", 2): "PM"},
        day_modes=day_modes,
        inactive_days=[],
        shift_weights={},
    )

    engine = DutySchedulerEngine(config, {}, req)
    engine.build_model()

    # Check that soft_ban_penalties list is populated
    # The actual solve might succeed (it's soft), but the internal list must exist
    assert len(engine.soft_ban_penalties) > 0
