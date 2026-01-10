"""
tests/test_core_scheduler.py

Tests specifically for the core scheduling logic and variable creation
within DutySchedulerEngine. Distinct from integration tests in test_scheduler.py.
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
        shift_weights={},  # Added
    )
    return config, req


def test_variable_creation(basic_setup):
    """Test that solver variables are created correctly."""
    config, req = basic_setup
    engine = DutySchedulerEngine(config, {}, req)
    engine._create_variables()

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
        shift_weights={},  # Added
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

    # 2. Duty -> S/B (AM on D1, S/B on D2) -> Should Fail
    req2 = SolverRequest(
        staff_ids=["A"],
        year=2025,
        month=1,
        fixed_assignments={("A", 1): "AM", ("A", 2): "S/B"},
        day_modes=day_modes,
        inactive_days=[],
        shift_weights={},
    )
    eng2 = DutySchedulerEngine(config, {}, req2)
    eng2.build_model()
    assert eng2.solve() is None, "AM followed by S/B should fail"

    # 3. S/B -> S/B (S/B on D1, S/B on D2) -> Should Fail
    req3 = SolverRequest(
        staff_ids=["A"],
        year=2025,
        month=1,
        fixed_assignments={("A", 1): "S/B", ("A", 2): "S/B"},
        day_modes=day_modes,
        inactive_days=[],
        shift_weights={},
    )
    eng3 = DutySchedulerEngine(config, {}, req3)
    eng3.build_model()
    assert eng3.solve() is None, "S/B followed by S/B should fail"
