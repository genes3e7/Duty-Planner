"""
tests/test_scheduler_constraints.py

Focus: Verification of specific business constraints.
Includes:
1. Transition Rules (Hard/Soft Bans)
2. Team Logic (Active/Standby separation)
3. Global Limits (Consecutive days, Catch-up limits)
"""

import pytest

from app.constants import RuleStatus
from app.core.scheduler import DutySchedulerEngine, SolverRequest
from app.models.config import AppConfig, RulesConfig


@pytest.fixture
def constraint_setup():
    """
    Minimal setup for constraint testing.
    Configured for 1 Person ("A") and minimal coverage (1 AM needed only).
    """
    cfg = AppConfig.default()
    cfg.personnel = ["A"]
    # RESET DEFAULT REQUIREMENTS to match single staff
    cfg.constraints.standby_per_day = 0
    cfg.constraints.personnel_needed_per_shift = {"AM": 1, "PM": 0, "24H": 0}

    # 2 Days to test transitions
    req = SolverRequest(
        staff_ids=["A"],
        year=2025,
        month=1,
        fixed_assignments={},
        day_modes={1: "SHIFT", 2: "SHIFT"},
        inactive_days=[],
        shift_weights={},
    )
    return cfg, req


# --- Transition Rule Tests ---


def test_hard_ban_enforcement(constraint_setup):
    """Verify Hard Ban prevents assignment."""
    cfg, req = constraint_setup

    # Rule: AM -> AM is Hard Ban
    cfg.rules.transitions["AM"]["AM"] = RuleStatus.HARD.value

    # Force Day 1 AM
    req.fixed_assignments = {("A", 1): "AM"}
    # Day 2 needs AM by default constraints

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    assert engine.solve() is None, "Solver ignored Hard Ban"


def test_rule_allowed_works(constraint_setup):
    """Verify Allowed transition works."""
    cfg, req = constraint_setup
    cfg.rules.transitions["AM"]["AM"] = RuleStatus.ALLOWED.value
    req.fixed_assignments = {("A", 1): "AM"}

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    assert engine.solve() is not None, "Solver failed on Allowed transition"


def test_soft_ban_penalty_generation(constraint_setup):
    """Verify Soft Ban generates penalty variables."""
    cfg, req = constraint_setup
    cfg.rules.transitions["AM"]["AM"] = RuleStatus.SOFT.value

    # Force the transition
    req.fixed_assignments = {("A", 1): "AM", ("A", 2): "AM"}

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()

    assert len(engine.soft_ban_penalties) > 0
    assert engine.solve() is not None


def test_rule_configuration_validity():
    """Test that RulesConfig validates structure correctly."""
    rc = RulesConfig()
    # Check default soft ban exists
    assert rc.transitions["AM"]["PM"] == RuleStatus.SOFT.value
    # Update rule
    rc.transitions["AM"]["PM"] = RuleStatus.ALLOWED.value
    assert rc.transitions["AM"]["PM"] == "Allowed"


# --- Physiological Limits ---


def test_consecutive_24h_hard_constraint(constraint_setup):
    """Verify implicit physiological rule: No consecutive 24H shifts."""
    cfg, req = constraint_setup
    req.day_modes = {1: "24H", 2: "24H"}

    # Force 24H back-to-back
    req.fixed_assignments = {("A", 1): "24H", ("A", 2): "24H"}
    # Ensure needs match 24H mode (1 person needed, 1 avail)
    cfg.constraints.personnel_needed_per_shift["24H"] = 1

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    assert engine.solve() is None


def test_no_duty_adjacent_to_sb(constraint_setup):
    """
    Verify S/B isolation.
    S/B cannot be adjacent to ANY duty (S/B, AM, PM, 24H).
    """
    cfg, req = constraint_setup
    # 3 days to test adjacency
    req.day_modes = {1: "SHIFT", 2: "SHIFT", 3: "SHIFT"}

    # S/B -> Duty (S/B on D1, AM on D2) -> Should Fail
    req.fixed_assignments = {("A", 1): "S/B", ("A", 2): "AM"}
    # Temporarily allow S/B logic to be valid if needed
    cfg.constraints.standby_per_day = 0  # Not enforcing coverage, just checking constraint violations

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    assert engine.solve() is None, "S/B followed by AM should fail"


# --- Team Logic Tests ---


def test_multi_team_coverage_independent():
    """Verify Team 1 and Team 2 coverage are enforced independently."""
    cfg = AppConfig.default()
    cfg.personnel = ["A", "B"]
    cfg.constraints.num_active_teams = 2
    # STRICT REQUIREMENTS: Only 1 AM per team. NO Standby.
    cfg.constraints.standby_per_day = 0
    cfg.constraints.personnel_needed_per_shift = {"AM": 1, "PM": 0, "24H": 0}

    # Day 1 Needs: Team 1 AM (1 person) + Team 2 AM (1 person) = 2 people total
    req = SolverRequest(
        staff_ids=["A", "B"],
        year=2025,
        month=1,
        fixed_assignments={},
        day_modes={1: "SHIFT"},
        inactive_days=[],
        shift_weights={},
    )

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    res = engine.solve()

    assert res is not None
    sched, _ = res
    # Both A and B must be working to satisfy AM_1 and AM_2 requirement
    assert len(sched) == 2
    shifts = list(sched.values())
    assert "AM" in shifts
    assert "AM_2" in shifts


# --- Catch Up Limit Tests ---


def test_catch_up_limit_zero_is_unlimited(constraint_setup):
    """Limit=0 should allow unlimited points."""
    cfg, req = constraint_setup
    cfg.personnel = ["A", "B", "C"]
    req.staff_ids = cfg.personnel  # <--- CRITICAL FIX: Sync req with config

    cfg.constraints.max_consecutive_duties = 20  # Relax for test
    cfg.constraints.catch_up_limit = 0.0  # Unlimited

    # Force A to do 8/10 days
    req.day_modes = {i: "SHIFT" for i in range(1, 11)}
    req.shift_weights = {(i, "AM"): 100 for i in range(1, 11)}
    for i in range(1, 9):
        req.fixed_assignments[("A", i)] = "AM"

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    assert engine.solve() is not None


def test_catch_up_limit_enforced_success(constraint_setup):
    """Valid assignment within limit should succeed."""
    cfg, req = constraint_setup
    cfg.personnel = ["A", "B", "C"]
    req.staff_ids = cfg.personnel  # <--- CRITICAL FIX

    cfg.constraints.max_consecutive_duties = 20

    # Avg = 3.3. Limit = 2.0. Max = 5.3.
    cfg.constraints.catch_up_limit = 2.0

    req.day_modes = {i: "SHIFT" for i in range(1, 11)}
    req.shift_weights = {(i, "AM"): 100 for i in range(1, 11)}

    # Force A to do 5 days (<= 5.3)
    for i in range(1, 6):
        req.fixed_assignments[("A", i)] = "AM"

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    assert engine.solve() is not None


def test_catch_up_limit_impossible_fail(constraint_setup):
    """Assignment exceeding limit should fail."""
    cfg, req = constraint_setup
    cfg.personnel = ["A", "B", "C"]
    req.staff_ids = cfg.personnel  # <--- CRITICAL FIX

    cfg.constraints.max_consecutive_duties = 20

    # Avg = 3.3. Limit = 1.0. Max = 4.3.
    cfg.constraints.catch_up_limit = 1.0

    req.day_modes = {i: "SHIFT" for i in range(1, 11)}
    req.shift_weights = {(i, "AM"): 100 for i in range(1, 11)}

    # Force A to do 6 days (> 4.3)
    for i in range(1, 7):
        req.fixed_assignments[("A", i)] = "AM"

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    assert engine.solve() is None


def test_catch_up_limit_distribution(constraint_setup):
    """Verify limit forces work distribution away from overloaded staff."""
    cfg, req = constraint_setup
    cfg.personnel = ["A", "B"]
    req.staff_ids = cfg.personnel  # <--- CRITICAL FIX

    cfg.constraints.catch_up_limit = 1.0

    # 30 Days. Total 30 shifts. Avg = 15. Max = 16.
    req.day_modes = {i: "SHIFT" for i in range(1, 31)}
    req.shift_weights = {(i, "AM"): 100 for i in range(1, 31)}

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    res = engine.solve()

    assert res is not None
    sched, _ = res
    a_count = sum(1 for (p, d) in sched.keys() if p == "A")
    assert a_count <= 16


def test_minimal_roster_nonzero_limit(constraint_setup):
    """Verify minimal roster (1 day) doesn't cause zero-division issues."""
    cfg, req = constraint_setup
    cfg.personnel = ["A", "B", "C"]
    req.staff_ids = cfg.personnel  # <--- CRITICAL FIX

    cfg.constraints.catch_up_limit = 0.8

    req.day_modes = {1: "SHIFT"}
    req.shift_weights = {(1, "AM"): 100}

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    assert engine.solve() is not None
