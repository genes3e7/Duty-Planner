from unittest.mock import mock_open, patch

from app.core.data import DataManager
from app.models.config import AppConfig


def test_load_config_defaults_on_missing_file():
    """Test that default config is returned if file is missing."""
    with patch("os.path.exists", return_value=False):
        cfg = DataManager.load_config()
        assert isinstance(cfg, AppConfig)
        assert cfg.year == 2025  # Check a default value


def test_save_config():
    """Test that config is saved to JSON correctly."""
    cfg = AppConfig.default()
    cfg.year = 2030

    with patch("builtins.open", mock_open()) as mock_file:
        DataManager.save_config(cfg)

        mock_file.assert_called_with("config.json", "w", encoding="utf-8")
        # Get the written content
        handle = mock_file()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)

        assert '"year": 2030' in written_data
