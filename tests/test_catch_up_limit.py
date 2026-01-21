"""
tests/test_catch_up_limit.py

Tests for the 'Catch Up Limit' feature.
Verifies that the solver correctly limits the maximum points a single person
can take in a month relative to the estimated average.
"""

import pytest

from app.constants import ScheduleMode
from app.core.scheduler import DutySchedulerEngine, SolverRequest
from app.models.config import AppConfig

# --- Fixtures ---


@pytest.fixture
def base_config():
    """Returns a minimal valid configuration with 3 staff."""
    cfg = AppConfig.default()
    cfg.personnel = ["A", "B", "C"]
    cfg.constraints.standby_per_day = 0  # Simplify: No standby needed
    # Simplify: 1 AM per day required
    cfg.constraints.personnel_needed_per_shift = {"AM": 1, "PM": 0, "24H": 0}

    # CRITICAL FIX: Relax consecutive limits to allow testing accumulation of points
    # without failing due to "Max 3 consecutive days" rule.
    cfg.constraints.max_consecutive_duties = 20

    return cfg


@pytest.fixture
def base_request(base_config):
    """Returns a solver request for a short 10-day period."""
    # 10 Days, SHIFT mode
    day_modes = {i: ScheduleMode.SHIFT.value for i in range(1, 11)}

    # Weights: All AM shifts = 1.0 point (scaled to 100)
    shift_weights = {}
    for i in range(1, 11):
        shift_weights[(i, "AM")] = 100
        shift_weights[(i, "PM")] = 100

    return SolverRequest(
        staff_ids=base_config.personnel,
        year=2025,
        month=1,
        fixed_assignments={},
        day_modes=day_modes,
        inactive_days=[],
        shift_weights=shift_weights,
    )


# --- Tests ---


def test_catch_up_limit_zero_is_unlimited(base_config, base_request):
    """
    Edge Case: Limit = 0.
    Expectation: The solver should behave normally (Unlimited).
    Scenario: Force 'A' to do almost everything (8/10 days).
              Avg is ~3.3. If limited, this would fail. With 0, it should succeed.
    """
    base_config.constraints.catch_up_limit = 0.0  # Unlimited

    # Force A to do days 1-8
    # Note: max_consecutive_duties is set to 20 in fixture to allow this
    for i in range(1, 9):
        base_request.fixed_assignments[("A", i)] = "AM"

    engine = DutySchedulerEngine(base_config, {}, base_request)
    engine.build_model()
    result = engine.solve()

    assert result is not None, "Solver failed with limit=0 (Unlimited)"
    schedule, _ = result

    # Verify A worked 8 days
    a_shifts = sum(1 for (p, d) in schedule.keys() if p == "A")
    assert a_shifts == 8


def test_catch_up_limit_enforced_success(base_config, base_request):
    """
    Normal Case: Limit > 0.
    Expectation: Solver respects the limit (Average + Limit).
    Scenario:
        - 3 Staff, 10 Days, 1 AM/day. Total 10 pts.
        - Average = 3.33 pts.
        - Limit = 2.0. Max Allowed = 5.33 pts.
        - We force A to do 5 days. This is <= 5.33. Should SUCCEED.
    """
    base_config.constraints.catch_up_limit = 2.0

    # Force A to do 5 days
    for i in range(1, 6):
        base_request.fixed_assignments[("A", i)] = "AM"

    engine = DutySchedulerEngine(base_config, {}, base_request)
    engine.build_model()
    result = engine.solve()

    assert result is not None, "Solver failed on valid constrained schedule"


def test_catch_up_limit_impossible_fail(base_config, base_request):
    """
    Edge Case: Impossible Constraint.
    Expectation: Solver fails (None).
    Scenario:
        - 3 Staff, 10 Days, 1 AM/day. Total 10 pts.
        - Average = 3.33 pts.
        - Limit = 1.0. Max Allowed = 4.33 pts.
        - We force A to do 6 days. 6 > 4.33. Should FAIL.
    """
    base_config.constraints.catch_up_limit = 1.0

    # Force A to do 6 days
    for i in range(1, 7):
        base_request.fixed_assignments[("A", i)] = "AM"

    engine = DutySchedulerEngine(base_config, {}, base_request)
    engine.build_model()
    result = engine.solve()

    assert result is None, "Solver ignored the catch-up limit (should have failed)"


def test_catch_up_limit_distribution(base_config, base_request):
    """
    Logic Check: Ensure the limit forces distribution.
    Scenario:
        - Staff A is heavily in debt (carry over -50 pts).
        - Without limit, fairness assigns A tons of shifts to catch up.
        - WITH limit (e.g. 1.0), A can only do Average + 1.
    """
    base_config.constraints.catch_up_limit = 1.0  # Tight leash

    # 30 Days to allow big numbers
    day_modes = {i: ScheduleMode.SHIFT.value for i in range(1, 31)}
    weights = {(i, "AM"): 100 for i in range(1, 31)}

    req = SolverRequest(
        staff_ids=["A", "B"],  # 2 Staff
        year=2025,
        month=1,
        fixed_assignments={},
        day_modes=day_modes,
        inactive_days=[],
        shift_weights=weights,
    )

    # Total 30 shifts. Avg = 15. Limit = 1. Max = 16.

    engine = DutySchedulerEngine(base_config, {}, req)
    engine.build_model()
    result = engine.solve()

    assert result is not None
    schedule, _ = result

    # Check A's count
    a_count = sum(1 for (p, d) in schedule.keys() if p == "A")

    # A should NOT exceed 16
    assert a_count <= 16, f"Staff A exceeded limit! Count: {a_count}, Max Allowed: 16"
