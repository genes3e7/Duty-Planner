import pytest

from app.constants import ScheduleMode
from app.core.scheduler import DutySchedulerEngine, SolverRequest
from app.models.config import AppConfig


@pytest.fixture
def basic_request():
    cfg = AppConfig.default()
    # Use just 3 people for simple testing
    cfg.personnel = ["A", "B", "C"]

    req = SolverRequest(
        staff_ids=cfg.personnel,
        year=2025,
        month=1,
        fixed_assignments={},
        day_modes={d: ScheduleMode.SHIFT.value for d in range(1, 32)},
        inactive_days=[],
    )
    return cfg, req


def test_solver_feasibility(basic_request):
    """Test that the solver finds a solution for a standard month."""
    cfg, req = basic_request

    # We need enough staff. 3 staff for 3 shifts (AM, PM, SB) is tight.
    # Increase to 6 staff to ensure feasibility.
    cfg.personnel = ["A", "B", "C", "D", "E", "F"]
    req.staff_ids = cfg.personnel

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    res = engine.solve()

    assert res is not None
    sched, summary = res
    assert len(sched) > 0
    # Ensure every active day has assignments
    # (Checking day 1 specifically)
    assignments_d1 = [p for (p, d) in sched.keys() if d == 1]
    assert len(assignments_d1) > 0


def test_solver_impossible_constraints(basic_request):
    """Test that solver correctly returns None when impossible."""
    cfg, req = basic_request
    # Requirement: 5 people per AM shift
    # Available: 3 people (from basic_request default)
    cfg.constraints.personnel_needed_per_shift["AM"] = 5

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
    res = engine.solve()

    assert res is not None
    sched, _ = res

    # Check result
    assert sched.get(("A", 1)) == "X"
