"""
tests/test_scheduling_rules.py

Tests for the 'Rules Configuration' feature.
Verifies that the solver respects dynamic Hard/Soft bans defined in config.
"""

import pytest

from app.constants import RuleStatus, ScheduleMode
from app.core.scheduler import DutySchedulerEngine, SolverRequest
from app.models.config import AppConfig, RulesConfig

# --- Fixtures ---


@pytest.fixture
def base_config():
    """Returns a minimal valid configuration with 1 staff member."""
    cfg = AppConfig.default()
    cfg.personnel = ["A"]
    cfg.constraints.standby_per_day = 0
    cfg.constraints.personnel_needed_per_shift = {"AM": 1, "PM": 0, "24H": 0}
    return cfg


@pytest.fixture
def base_request(base_config):
    """Returns a request for 2 days."""
    return SolverRequest(
        staff_ids=base_config.personnel,
        year=2025,
        month=1,
        fixed_assignments={},
        day_modes={1: ScheduleMode.SHIFT.value, 2: ScheduleMode.SHIFT.value},
        inactive_days=[],
        shift_weights={},
    )


# --- Tests ---


def test_rule_hard_ban_enforcement(base_config, base_request):
    """
    Edge Case: Hard Ban.
    Expectation: Transition is strictly forbidden.
    Scenario:
        - Force Day 1: AM.
        - Rule: AM -> AM is HARD BAN.
        - Result: Solver should FAIL because A cannot work D2 (and coverage requires it).
    """
    # Configure Rule: AM -> AM = Hard Ban
    base_config.rules.transitions["AM"]["AM"] = RuleStatus.HARD.value

    # Force A to work Day 1
    base_request.fixed_assignments = {("A", 1): "AM"}

    # Coverage needs 1 AM on Day 2. Staff is only A.
    # Transition A(AM)->A(AM) is Hard Banned.

    engine = DutySchedulerEngine(base_config, {}, base_request)
    engine.build_model()
    result = engine.solve()

    assert result is None, "Solver ignored Hard Ban on AM->AM transition"


def test_rule_allowed_works(base_config, base_request):
    """
    Edge Case: Allowed.
    Expectation: Solver succeeds.
    Scenario: Same as above, but AM->AM is ALLOWED.
    """
    base_config.rules.transitions["AM"]["AM"] = RuleStatus.ALLOWED.value

    base_request.fixed_assignments = {("A", 1): "AM"}

    engine = DutySchedulerEngine(base_config, {}, base_request)
    engine.build_model()
    result = engine.solve()

    assert result is not None, "Solver failed on Allowed transition"


def test_rule_soft_ban_penalty(base_config, base_request):
    """
    Edge Case: Soft Ban.
    Expectation: Solution found, but penalty variables generated.
    """
    base_config.rules.transitions["AM"]["AM"] = RuleStatus.SOFT.value

    # Force the transition
    base_request.fixed_assignments = {("A", 1): "AM", ("A", 2): "AM"}

    engine = DutySchedulerEngine(base_config, {}, base_request)
    engine.build_model()

    # Verify the model created penalty variables
    assert len(engine.soft_ban_penalties) > 0, "No soft ban penalties generated"

    # Solve should still succeed (it's soft)
    result = engine.solve()
    assert result is not None, "Solver failed on Soft Ban (should be allowed with penalty)"


def test_rule_configuration_validity():
    """
    Test that the RulesConfig Pydantic model validates structure correctly.
    """
    # 1. Valid structure initialization
    rc = RulesConfig()
    # Check default soft ban exists
    assert rc.transitions["AM"]["PM"] == RuleStatus.SOFT.value

    # 2. Update rule
    rc.transitions["AM"]["PM"] = RuleStatus.ALLOWED.value
    assert rc.transitions["AM"]["PM"] == "Allowed"

    # 3. Check integration with AppConfig
    app_cfg = AppConfig.default()
    assert "transitions" in app_cfg.rules.model_dump()
