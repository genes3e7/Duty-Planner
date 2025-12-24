"""
test_scheduler.py

Unit tests for v3.0.0 Architecture using pytest.
Includes coverage for Solver Logic, Constraints, and Edge Cases.
"""

import pytest

from app.constants import ShiftType
from app.core.scheduler import DutySchedulerEngine, SolverRequest
from app.models.config import AppConfig


@pytest.fixture
def scheduler_data():
    """
    Fixture that provides a fresh setup (Config, Previous Balance, SolverRequest)
    for every single test function.
    """
    cfg = AppConfig.default()
    # Use 6 personnel.
    # Daily need = 1 AM + 1 PM + 1 S/B = 3 shifts.
    # Gap rule requires ~2x manpower, so 6 is the minimum feasible number.
    cfg.personnel = ["A", "B", "C", "D", "E", "F"]

    # Ensure default constraints are set clearly
    cfg.constraints.personnel_needed_per_shift = {
        ShiftType.AM.value: 1,
        ShiftType.PM.value: 1,
        ShiftType.FULL_24H.value: 1,  # Only used in 24H mode
    }
    cfg.constraints.standby_per_day = 1

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


def test_strict_gap_rule(scheduler_data):
    """
    Test that no personnel is assigned shifts on consecutive days.
    (e.g., if working Day 1, cannot work Day 2).
    """
    cfg, prev, req = scheduler_data
    eng = DutySchedulerEngine(cfg, prev, req)
    eng.build_model()
    res = eng.solve()

    assert res is not None
    sched, _ = res

    for person in cfg.personnel:
        # Get list of days this person is working
        days_worked = sorted([d for (p, d) in sched.keys() if p == person])

        # Check for consecutive days
        for i in range(len(days_worked) - 1):
            assert days_worked[i + 1] != days_worked[i] + 1, (
                f"Person {person} worked consecutive days: "
                f"{days_worked[i]} and {days_worked[i + 1]}"
            )


def test_fixed_assignment_duty(scheduler_data):
    """Test that manual duty assignments (forced in UI) are respected."""
    cfg, prev, req = scheduler_data

    target_day = 5
    target_person = "A"
    target_shift = ShiftType.AM

    # Force Person A to do AM on Day 5
    req.fixed_assignments = {(target_person, target_day): target_shift}

    eng = DutySchedulerEngine(cfg, prev, req)
    eng.build_model()
    res = eng.solve()

    assert res is not None
    sched, _ = res

    # Assert assignment exists
    assert sched.get((target_person, target_day)) == target_shift


def test_fixed_assignment_leave(scheduler_data):
    """Test that manual LEAVE assignments prevent any duty on that day."""
    cfg, prev, req = scheduler_data

    target_day = 5
    target_person = "A"

    # Force Person A to be on LEAVE (X) on Day 5
    req.fixed_assignments = {(target_person, target_day): ShiftType.LEAVE}

    eng = DutySchedulerEngine(cfg, prev, req)
    eng.build_model()
    res = eng.solve()

    assert res is not None
    sched, _ = res

    # Assert Person A has NO entry for Day 5
    assert (target_person, target_day) not in sched


def test_daily_manpower_validation(scheduler_data):
    """
    Validate that every active day has exactly the required number of
    AM, PM, and Standby personnel.
    """
    cfg, prev, req = scheduler_data
    eng = DutySchedulerEngine(cfg, prev, req)
    eng.build_model()
    res = eng.solve()

    assert res is not None
    sched, _ = res

    # Check first 5 days
    for d in range(1, 6):
        shifts_on_day = [s for (p, day), s in sched.items() if day == d]

        am_count = shifts_on_day.count(ShiftType.AM)
        pm_count = shifts_on_day.count(ShiftType.PM)
        sb_count = shifts_on_day.count(ShiftType.STANDBY)

        assert am_count == 1, f"Day {d} missing AM shift"
        assert pm_count == 1, f"Day {d} missing PM shift"
        assert sb_count == 1, f"Day {d} missing Standby"


def test_insufficient_resources(scheduler_data):
    """
    Test that the solver correctly fails (returns None) if there
    aren't enough people to meet constraints.
    """
    cfg, prev, req = scheduler_data

    # Daily requirement = 3 shifts (1 AM, 1 PM, 1 SB)
    # Gap rule implies we need > 3 people.
    # Reducing staff to 2 should make the schedule impossible.
    req.staff_ids = ["A", "B"]

    eng = DutySchedulerEngine(cfg, prev, req)
    eng.build_model()
    res = eng.solve()

    # Expecting NO solution
    assert res is None
