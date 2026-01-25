"""
tests/test_unit_utils.py

Focus: Unit tests for utility modules (Helpers, Data Manager).
Verifies:
1. String manipulation for shift suffixes.
2. Excel file parsing and error handling.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from app.core.data import DataManager
from app.utils import helpers

# --- Helper Tests (from test_helpers.py) ---


def test_get_shift_name():
    """Test shift name generation logic."""
    assert helpers.get_shift_name("AM", 1) == "AM"
    assert helpers.get_shift_name("S/B", 1) == "S/B"
    assert helpers.get_shift_name("AM", 2) == "AM_2"
    assert helpers.get_shift_name("24H", 10) == "24H_10"


def test_get_base_shift_type():
    """Test extraction of base type from string."""
    assert helpers.get_base_shift_type("AM") == "AM"
    assert helpers.get_base_shift_type("AM_2") == "AM"
    assert helpers.get_base_shift_type("S/B_2") == "S/B"


# --- Data Manager Tests (from test_data.py) ---


def test_load_previous_balance_valid():
    """Test loading valid balance data from Excel."""
    mock_df = pd.DataFrame({"Name": ["Alice", "Bob"], "Carry Over": [10.5, 5.0]})

    with patch("pandas.read_excel", return_value=mock_df):
        result = DataManager.load_previous_balance("dummy.xlsx")

    assert result["Alice"] == 10.5
    assert result["Bob"] == 5.0


def test_load_previous_balance_missing_columns():
    """Test that ValueError is raised if columns missing."""
    mock_df = pd.DataFrame({"Name": ["Alice"]})  # Missing 'Carry Over'

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


def test_load_constraints_valid():
    """Test loading valid constraints from Excel."""
    mock_df = pd.DataFrame({"Name": ["Alice", "Bob"], "1": ["AM", None], "2": [None, "X"]})

    with patch("pandas.read_excel", return_value=mock_df):
        result = DataManager.load_constraints("dummy.xlsx")

    assert result["Alice"][1] == "AM"
    assert result["Bob"][2] == "X"


def test_load_constraints_missing_name_column():
    """Test failure when 'Name' column is missing."""
    mock_df = pd.DataFrame({"Day1": ["AM"]})
    with patch("pandas.read_excel", return_value=mock_df):
        with pytest.raises(ValueError, match="must contain 'Name'"):
            DataManager.load_constraints("dummy.xlsx")
