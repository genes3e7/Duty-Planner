import pytest

from app.constants import ScheduleMode
from app.core.scheduler import DutySchedulerEngine, SolverRequest
from app.models.config import AppConfig


@pytest.fixture
def basic_request():
    cfg = AppConfig.default()
    cfg.personnel = ["A", "B"]

    req = SolverRequest(
        staff_ids=cfg.personnel,
        year=2025,
        month=1,
        fixed_assignments={},
        # Fix raw string usage
        day_modes={1: ScheduleMode.SHIFT.value, 2: ScheduleMode.SHIFT.value},
        inactive_days=[],
    )
    return cfg, req


def test_no_consecutive_24h_shifts():
    """Test that a 24H shift on day D prevents assignments on day D+1."""
    cfg = AppConfig.default()
    # Need sufficient people to cover Day 2 while A rests.
    # Day 1: A works 24H.
    # Day 2 Requirements:
    #   - AM: 1
    #   - PM: 1
    #   - S/B: 1 (Default in AppConfig)
    #   - Total needed: 3 distinct people.
    # A is resting. We need 3 others.
    # Providing 5 people (A, B, C, D, E) ensures we have 4 available for 3 slots, guaranteeing feasibility.
    cfg.personnel = ["A", "B", "C", "D", "E"]

    # Alternatively, we could lower constraints, but adding people is safer/clearer.

    # We must set Day 1 to 24H mode so the solver creates 24H variables
    req = SolverRequest(
        staff_ids=cfg.personnel,
        year=2025,
        month=1,
        fixed_assignments={("A", 1): "24H"},
        # Day 1 is 24H mode, Day 2 is SHIFT mode
        day_modes={1: ScheduleMode.FULL_24H.value, 2: ScheduleMode.SHIFT.value},
        inactive_days=[],
    )

    engine = DutySchedulerEngine(cfg, {}, req)
    engine.build_model()
    result = engine.solve()

    assert result is not None, (
        "Solver should find a solution. If failing, check if enough staff exist "
        "to cover Day 2 (AM+PM+SB) while A rests."
    )
    sched, _ = result

    # Check that day 2 is empty for A (simplified assertion)
    assert sched.get(("A", 2)) is None, "A should have no duties on day 2 after a 24H shift"

    # Check that day 2 is covered by someone else to prove D2 was active
    assignments_d2_any = [k for k, v in sched.items() if k[1] == 2]
    assert len(assignments_d2_any) > 0, "Day 2 should have assignments"
