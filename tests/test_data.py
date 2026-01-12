"""
tests/test_data.py
"""

from unittest.mock import mock_open, patch

import pandas as pd
import pytest

from app.core.data import DataManager
from app.models.config import AppConfig

# --- Save Config Tests ---


def test_save_config_success():
    """Test successful save returns True and fsync is called."""
    cfg = AppConfig.default()
    test_path = "test_config.json"
    with patch("builtins.open", mock_open()):
        with patch("os.path.exists", return_value=True):
            with patch("os.replace") as mock_replace:
                # Mock fsync to avoid "fileno() returned a non-integer" error
                with patch("os.fsync") as mock_fsync:
                    success = DataManager.save_config(cfg, test_path)
                    assert success is True
                    mock_replace.assert_called_once()
                    mock_fsync.assert_called_once()


def test_save_config_failure():
    """Test that save returns False on write error."""
    cfg = AppConfig.default()
    test_path = "test_config.json"
    with patch("builtins.open", side_effect=IOError("disk full")):
        success = DataManager.save_config(cfg, test_path)
        assert success is False


# --- Load Previous Balance Tests ---


def test_load_previous_balance_valid():
    """Test loading valid balance data from Excel."""
    mock_df = pd.DataFrame({"Name": ["Alice", "Bob"], "Carry Over": [10.5, 5.0], "Extra": ["Ignore", "Me"]})

    with patch("pandas.read_excel", return_value=mock_df):
        result = DataManager.load_previous_balance("dummy.xlsx")

    assert result["Alice"] == 10.5
    assert result["Bob"] == 5.0
    assert len(result) == 2


def test_load_previous_balance_missing_columns():
    """Test that ValueError is raised if required columns are missing."""
    mock_df = pd.DataFrame({"Name": ["Alice"], "Points": [10]})  # Missing 'Carry Over'

    with patch("pandas.read_excel", return_value=mock_df):
        with pytest.raises(ValueError, match="must contain 'Name' and 'Carry Over'"):
            DataManager.load_previous_balance("dummy.xlsx")


def test_load_previous_balance_empty_input():
    """Test that None or empty input returns empty dict."""
    assert DataManager.load_previous_balance(None) == {}
    assert DataManager.load_previous_balance("") == {}


def test_load_previous_balance_corrupt_values():
    """Test that non-numeric carry over values are skipped."""
    mock_df = pd.DataFrame({"Name": ["Alice", "Bob"], "Carry Over": ["NotANumber", 5.0]})

    with patch("pandas.read_excel", return_value=mock_df):
        result = DataManager.load_previous_balance("dummy.xlsx")

    # Alice should be skipped
    assert "Alice" not in result
    assert result["Bob"] == 5.0


# --- Load Constraints Tests ---


def test_load_constraints_valid():
    """Test loading valid constraints from Excel."""
    # Structure: Name, 1, 2, 3 (Days)
    mock_df = pd.DataFrame({"Name": ["Alice", "Bob"], "1": ["AM", None], "2": [None, "X"], "3": ["PM", "24H"]})

    with patch("pandas.read_excel", return_value=mock_df):
        result = DataManager.load_constraints("dummy.xlsx")

    assert result["Alice"][1] == "AM"
    assert result["Alice"][3] == "PM"
    assert 2 not in result["Alice"]

    assert result["Bob"][2] == "X"
    assert result["Bob"][3] == "24H"


def test_load_constraints_missing_name_column():
    """Test failure when 'Name' column is missing."""
    mock_df = pd.DataFrame({"Day1": ["AM"]})
    with patch("pandas.read_excel", return_value=mock_df):
        with pytest.raises(ValueError, match="must contain 'Name'"):
            DataManager.load_constraints("dummy.xlsx")
