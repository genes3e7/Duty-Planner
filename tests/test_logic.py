import pytest
import pandas as pd
from app import logic
from app.models.config import AppConfig

@pytest.fixture
def default_config():
    """Returns a default configuration object."""
    return AppConfig.default()

@pytest.fixture
def mock_roster_data(default_config):
    """Creates a basic roster and days dataframe for testing."""
    year, month = 2024, 1
    # Use the logic function to generate structure
    roster, days = logic.generate_empty_schedule(year, month, default_config.personnel)
    return roster, days

def test_generate_empty_schedule(default_config):
    """Test structure of generated dataframes."""
    roster, days = logic.generate_empty_schedule(2025, 1, default_config.personnel)
    
    # Check Roster
    assert isinstance(roster, pd.DataFrame)
    # Roster columns should be strings based on recent fixes
    assert all(isinstance(c, str) for c in roster.columns)
    assert len(roster.index) == len(default_config.personnel)
    
    # Check Days
    assert isinstance(days, pd.DataFrame)
    assert "Active" in days.columns
    assert "Mode" in days.columns
    assert len(days) == 31  # Jan has 31 days

def test_prepare_solver_request(default_config, mock_roster_data):
    """Test that UI dataframes are correctly converted to SolverRequest."""
    roster, days = mock_roster_data
    
    # 1. Setup specific data
    person = default_config.personnel[0]
    # Set day "5" (String column) to "X"
    roster.at[person, "5"] = "X" 
    
    # Disable day 10
    days.at[10, "Active"] = False
    
    # 2. Execute
    req = logic.prepare_solver_request(2024, 1, roster, days, default_config)
    
    # 3. Verify
    # Check assignments: (Person, DayInt) -> Value
    assert (person, 5) in req.fixed_assignments
    assert req.fixed_assignments[(person, 5)] == "X"
    
    # Check inactive days
    assert 10 in req.inactive_days

def test_calculate_stats_logic(default_config, mock_roster_data):
    """Test the points calculation logic."""
    roster, days = mock_roster_data
    person = default_config.personnel[0]
    
    # --- CONFIGURATION FOR TEST ---
    # Set explicit values to ensure test doesn't break if defaults change
    default_config.points.AM = 1.0
    default_config.points.weekend_multiplier = 1.5
    default_config.points.weekend_is_multiplier = True
    
    # --- SCENARIO 1: Standard Duty ---
    # Day 2 is a standard weekday (Jan 2 2024 was Tuesday)
    days.at[2, "Is_Weekend"] = False
    days.at[2, "Is_PH"] = False
    roster.at[person, "2"] = "AM"
    
    # --- SCENARIO 2: Weekend Duty ---
    # Day 6 is a weekend (Jan 6 2024 was Saturday)
    days.at[6, "Is_Weekend"] = True
    days.at[6, "Is_PH"] = False
    roster.at[person, "6"] = "AM"
    
    # --- EXECUTE ---
    stats = logic.calculate_stats(roster, days, default_config, prev_balance={})
    
    # --- VERIFY ---
    # Get stats for the specific person
    person_stats = stats[stats["Name"] == person].iloc[0]
    
    # Expected: 1.0 (Day 2) + 1.5 (Day 6: 1.0 * 1.5) = 2.5
    assert person_stats["Month Pts"] == 2.5
