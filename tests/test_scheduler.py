import statistics

import pytest

from app.constants import ScheduleMode
from app.core.scheduler import DutySchedulerEngine, SolverRequest
from app.models.config import AppConfig


@pytest.fixture
def basic_request():
    cfg = AppConfig.default()
    # increased to 6 people to ensure feasibility with AM=1, PM=1, SB=1 and max_consecutive=3
    cfg.personnel = ["A", "B", "C", "D", "E", "F"]

    req = SolverRequest(
        staff_ids=cfg.personnel,
        year=2025,
        month=1,
        fixed_assignments={},
        # Changed from ScheduleMode.SHIFT.value to ScheduleMode.SHIFT
        day_modes={d: ScheduleMode.SHIFT.value for d in range(1, 32)},
        inactive_days=[],
    )
    return cfg, req


def test_solver_basic_feasibility(basic_request):
    """Test that the solver finds a solution for a standard month."""
    cfg, req = basic_request
    # Passed empty dict {} is for 'prev_balance' (initial points)
    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    result = engine.solve()

    assert result is not None
    sched, summary = result
    assert len(sched) > 0
    # Ensure every active day has assignments
    # (Checking day 1 specifically)
    assignments_d1 = [p for (p, d), s in sched.items() if d == 1]
    # We expect 3 assignments: 1 AM, 1 PM, 1 SB (default constraints)
    assert len(assignments_d1) >= 3


def test_solver_impossible_constraints(basic_request):
    """Test that solver correctly fails when constraints cannot be met."""
    cfg, req = basic_request
    # Requirement: 10 people per AM shift (more than total staff)
    cfg.constraints.personnel_needed_per_shift["AM"] = 10

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    result = engine.solve()

    assert result is None  # Should be impossible


def test_solver_respects_fixed_assignments(basic_request):
    """Test that manually assigned 'X's are respected."""
    cfg, req = basic_request
    # Force 'A' to be on leave (X) on Day 1
    req.fixed_assignments = {("A", 1): "X"}

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    result = engine.solve()

    assert result is not None, "Solver returned None, expected valid schedule"
    sched, _ = result

    # Check result
    assert sched.get(("A", 1)) == "X"


def test_solver_fairness_std_dev():
    """
    Test that the solver produces a fair schedule (low standard deviation)
    when given enough resources and no constraints.
    """
    cfg = AppConfig.default()
    # 10 Staff, 30 Days
    cfg.personnel = [f"Staff_{i}" for i in range(1, 11)]

    # Needs: 1 AM, 1 PM (2 duties/day) + 1 SB = 3 duties/day.
    # Total duties = 3 * 30 = 90.
    # 90 duties / 10 staff = 9 duties per person on average.

    req = SolverRequest(
        staff_ids=cfg.personnel,
        year=2025,
        month=6,  # 30 days
        fixed_assignments={},
        day_modes={d: "SHIFT" for d in range(1, 31)},
        inactive_days=[],
    )

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    result = engine.solve()

    assert result is not None
    sched, _ = result

    # Calculate points per person
    person_points = {p: 0.0 for p in cfg.personnel}

    for (p, _), shift in sched.items():  # Fixed unused variable 'd'
        if shift in ["AM", "PM", "S/B"]:  # Include S/B in count if it has points (default 0 or handled)
            # For this test, let's assume simple count equality is what we want to measure,
            # or rely on config points. Default points: AM=1, PM=1, SB=? (Undefined in PointsConfig usually)
            # Let's trust the engine's objective function which uses configured points.
            try:
                pts = cfg.points.get_by_type(shift)
            except ValueError:
                pts = 0.0
            person_points[p] += pts

    points_list = list(person_points.values())
    stdev = statistics.stdev(points_list)

    # Assert standard deviation is low
    assert stdev < 2.0, f"Standard Deviation {stdev} is too high, schedule is not fair: {points_list}"
