"""
tests/test_data.py
"""

from unittest.mock import mock_open, patch

from app.core.data import DataManager
from app.models.config import AppConfig


def test_save_config_success():
    """Test successful save returns True."""
    cfg = AppConfig.default()
    with patch("builtins.open", mock_open()):
        with patch("os.path.exists", return_value=True):
            with patch("os.replace") as mock_replace:
                success = DataManager.save_config(cfg)
                assert success is True
                mock_replace.assert_called_once()


def test_save_config_failure():
    """Test that save returns False on write error."""
    cfg = AppConfig.default()
    with patch("builtins.open", side_effect=IOError("disk full")):
        success = DataManager.save_config(cfg)
        assert success is False
