import json
from unittest.mock import mock_open, patch

import pytest

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
    """Test successful save returns True and writes correct content."""
    cfg = AppConfig.default()
    with patch("builtins.open", mock_open()) as m:
        # Also patch os.replace and os.remove to prevent actual file system ops that fail
        # when the source file doesn't actually exist (because open was mocked)
        with patch("os.replace") as mock_replace:
            success = DataManager.save_config(cfg)
            assert success is True
            # Verify call arguments
            m.assert_called_once_with("config.json.tmp", "w", encoding="utf-8")

            # Verify JSON was written
            written_data = "".join(call.args[0] for call in m().write.call_args_list)
            parsed = json.loads(written_data)
            assert "personnel" in parsed
            assert len(parsed["personnel"]) == 20

            # Verify replace was called
            mock_replace.assert_called_once_with("config.json.tmp", "config.json")


def test_load_previous_balance_parsing():
    """Test loading balance from an Excel file mock."""
    import pandas as pd

    mock_df = pd.DataFrame({"Name": ["Alice", "Bob"], "Carry Over": [10.5, 5.0], "Other": [1, 2]})

    with patch("pandas.read_excel", return_value=mock_df):
        balance = DataManager.load_previous_balance("dummy.xlsx")
        assert balance["Alice"] == 10.5
        assert balance["Bob"] == 5.0
        assert "Charlie" not in balance


def test_load_previous_balance_missing_columns():
    """Test that missing required columns raises ValueError."""
    import pandas as pd

    mock_df = pd.DataFrame({"Other": ["Alice"], "Data": [10.5]})
    with patch("pandas.read_excel", return_value=mock_df):
        # The regex string needs to match the actual error message raised in data.py
        # Actual message: "Excel file must contain 'Name' and 'Carry Over' columns."
        with pytest.raises(ValueError, match="must contain 'Name' and 'Carry Over'"):
            DataManager.load_previous_balance("dummy.xlsx")


def test_load_previous_balance_skips_invalid_values():
    """Test that non-numeric balance values are skipped."""
    import pandas as pd

    mock_df = pd.DataFrame({"Name": ["Alice", "Bob"], "Carry Over": [10.5, "invalid"]})
    with patch("pandas.read_excel", return_value=mock_df):
        balance = DataManager.load_previous_balance("dummy.xlsx")
        assert balance["Alice"] == 10.5
        assert "Bob" not in balance
