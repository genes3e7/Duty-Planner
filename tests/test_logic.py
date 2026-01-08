import pandas as pd
import pytest
from app import logic
from app.constants import ShiftType

def test_generate_schedule_structure(default_config):
    """Test that the empty schedule has correct dimensions and indexes."""
    roster, days = logic.generate_empty_schedule(2025, 1, default_config.personnel)
    
    assert len(roster) == 3  # 3 personnel
    assert len(roster.columns) == 31  # Jan has 31 days
    assert "Alice" in roster.index
    
    assert len(days) == 31
    assert "Active" in days.columns
    assert "Mode" in days.columns

def test_calculate_stats_logic(default_config, mock_roster_data):
    """Test points calculation including multipliers."""
    roster, days = mock_roster_data
    
    # 1. Setup Scenario
    # Alice works Day 1 (PH) -> Should be 1.0 * PH Multiplier (2.0) = 2.0
    # Bob works Day 4 (Weekend) -> Should be 1.0 * Weekend Multiplier (1.5) = 1.5
    # Charlie works Day 2 (Normal) -> 1.0
    
    # Mock PH/Weekend status in days df
    days.at[1, "Is_PH"] = True
    days.at[4, "Is_Weekend"] = True
    days.at[2, "Is_PH"] = False
    days.at[2, "Is_Weekend"] = False
    
    roster.at["Alice", 1] = ShiftType.AM
    roster.at["Bob", 4] = ShiftType.AM
    roster.at["Charlie", 2] = ShiftType.AM
    
    prev_balance = {"Alice": 10.0} # Alice brings fwd 10 pts
    
    stats = logic.calculate_stats(roster, days, default_config, prev_balance)
    stats.set_index("Name", inplace=True)
    
    assert stats.at["Alice", "Month Pts"] == 2.0
    assert stats.at["Alice", "Carry Over"] == 12.0
    assert stats.at["Bob", "Month Pts"] == 1.5
    assert stats.at["Charlie", "Month Pts"] == 1.0

def test_prepare_solver_request(default_config, mock_roster_data):
    """Test that UI dataframes are correctly converted to SolverRequest."""
    roster, days = mock_roster_data
    
    # Set a fixed assignment
    roster.at["Alice", 5] = "X" # Leave
    
    # Set an inactive day
    days.at[10, "Active"] = False
    
    req = logic.prepare_solver_request(2025, 1, roster, days, default_config)
    
    assert req.year == 2025
    assert ("Alice", 5) in req.fixed_assignments
    assert req.fixed_assignments[("Alice", 5)] == "X"
    assert 10 in req.inactive_days
