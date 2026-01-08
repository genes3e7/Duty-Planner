import pytest
from app.models.config import AppConfig

@pytest.fixture
def default_config():
    """Returns a standard AppConfig for testing."""
    cfg = AppConfig.default()
    cfg.personnel = ["Alice", "Bob", "Charlie"]
    return cfg

@pytest.fixture
def mock_roster_data(default_config):
    """Returns a tuple of (RosterDF, DayDF) populated for Jan 2025."""
    from app.logic import generate_empty_schedule
    return generate_empty_schedule(2025, 1, default_config.personnel)
