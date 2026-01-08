from unittest.mock import mock_open, patch

from app.core.data import DataManager
from app.models.config import AppConfig


def test_load_config_missing_file():
    """Ensure defaults are returned if config file is missing."""
    with patch("os.path.exists", return_value=False):
        cfg = DataManager.load_config("missing.json")
        assert isinstance(cfg, AppConfig)
        assert len(cfg.personnel) == 20  # Default


def test_load_config_corrupted_file():
    """Ensure defaults are returned if config file is invalid JSON."""
    with patch("builtins.open", mock_open(read_data="{invalid_json")):
        with patch("os.path.exists", return_value=True):
            cfg = DataManager.load_config("bad.json")
            assert isinstance(cfg, AppConfig)


def test_save_config_success():
    """Test successful save returns True."""
    cfg = AppConfig.default()
    with patch("builtins.open", mock_open()) as m:
        success = DataManager.save_config(cfg)
        assert success is True
        m.assert_called_once()


def test_load_previous_balance_parsing():
    """Test loading balance from an Excel file mock."""
    # Create a dummy dataframe matching the expected format
    import pandas as pd

    mock_df = pd.DataFrame({"Name": ["Alice", "Bob"], "Carry Over": [10.5, 5.0], "Other": [1, 2]})

    with patch("pandas.read_excel", return_value=mock_df):
        balance = DataManager.load_previous_balance("dummy.xlsx")
        assert balance["Alice"] == 10.5
        assert balance["Bob"] == 5.0
        assert "Charlie" not in balance
