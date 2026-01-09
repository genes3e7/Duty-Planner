import pytest

from app.constants import ScheduleMode
from app.core.scheduler import DutySchedulerEngine, SolverRequest
from app.models.config import AppConfig


@pytest.fixture
def basic_request():
    """
    Creates a basic feasible request.
    Requirements: AM=1, PM=1, 24H=1, SB=1 -> Total 4 slots/day.
    Personnel: 6 (Safely covers the 4 slots + rest days).
    """
    cfg = AppConfig.default()
    # Increase personnel to ensure feasibility with strict constraints
    cfg.personnel = ["A", "B", "C", "D", "E", "F"]
    cfg.constraints.personnel_needed_per_shift = {"AM": 1, "PM": 1, "24H": 1}
    cfg.constraints.standby_per_day = 1

    # Create day modes for a full 31-day month
    day_modes = {d: ScheduleMode.SHIFT.value for d in range(1, 32)}

    req = SolverRequest(
        staff_ids=cfg.personnel,
        year=2025,
        month=1,
        fixed_assignments={},
        day_modes=day_modes,
        inactive_days=[],
    )
    return cfg, req


def test_solver_basic_feasibility(basic_request):
    """Test that the solver finds a solution for a standard month."""
    cfg, req = basic_request
    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    result = engine.solve()

    assert result is not None, "Solver returned None, expected valid schedule"
    sched, _ = result
    assert len(sched) > 0


def test_solver_respects_fixed_assignments(basic_request):
    """Test that manually assigned 'X's are respected."""
    cfg, req = basic_request
    # Force 'A' to be on leave (X) on Day 1
    req.fixed_assignments = {("A", 1): "X"}

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    result = engine.solve()

    assert result is not None
    sched, _ = result
    assert sched.get(("A", 1)) == "X"


def test_solver_respects_fixed_duty(basic_request):
    """Test that manually assigned duties are respected."""
    cfg, req = basic_request
    # Force 'A' to be AM on Day 1
    req.fixed_assignments = {("A", 1): "AM"}

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    result = engine.solve()

    assert result is not None
    sched, _ = result
    assert sched.get(("A", 1)) == "AM"


def test_no_consecutive_24h_shifts(basic_request):
    """Test that a person is not assigned 24H back-to-back."""
    cfg, req = basic_request
    # Force 'A' to be 24H on Day 1
    req.fixed_assignments = {("A", 1): "24H"}

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    result = engine.solve()

    assert result is not None
    sched, _ = result

    # Check Day 2 for 'A' - strictly should be empty (rest)
    # The solver logic forces all vars to 0 on D+1 after a 24H shift
    # So 'A' should not be in the schedule for Day 2, or mapped to ""
    assignment_day_2 = sched.get(("A", 2))
    assert assignment_day_2 is None or assignment_day_2 == ""
