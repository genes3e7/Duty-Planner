import pytest
from app.core.scheduler import DutySchedulerEngine, SolverRequest
from app.constants import ShiftType

def test_solver_feasibility(default_config):
    """Test that the solver finds a solution for a standard month."""
    req = SolverRequest(
        staff_ids=default_config.personnel,
        year=2025, 
        month=1,
        fixed_assignments={},
        day_modes={},
        inactive_days=[]
    )
    
    # We need enough staff. 3 staff for 3 shifts (AM, PM, SB) is tight but possible without gaps?
    # Actually, with gap rule, 3 staff for 3 daily slots is IMPOSSIBLE.
    # Person A works Day 1. Cannot work Day 2.
    # We need to increase staff for this test to pass.
    default_config.personnel = ["A", "B", "C", "D", "E", "F"]
    req.staff_ids = default_config.personnel
    
    engine = DutySchedulerEngine(default_config, {}, req)
    engine.build_model()
    res = engine.solve()
    
    assert res is not None
    sched, summary = res
    assert len(sched) > 0

def test_solver_impossible_constraints(default_config):
    """Test that solver correctly returns None when impossible."""
    # Only 1 person available, but 3 shifts needed per day
    default_config.personnel = ["LoneWolf"]
    req = SolverRequest(
        staff_ids=default_config.personnel,
        year=2025, month=1,
        fixed_assignments={}, day_modes={}, inactive_days=[]
    )
    
    engine = DutySchedulerEngine(default_config, {}, req)
    engine.build_model()
    res = engine.solve()
    
    assert res is None
