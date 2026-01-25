"""
tests/test_config_lifecycle.py

Focus: The lifecycle of the configuration object.
1. Loading from File (Server)
2. Merging updates (Upload)
3. Serialization (Download)
"""

import json

import pytest

from app.core.data import DataManager
from app.models.config import AppConfig

# --- Fixtures ---


@pytest.fixture
def server_config_file(tmp_path):
    """Creates a temporary 'server-side' config.json file."""
    config_data = {
        "year": 2026,
        "month": 5,
        "country_code": "SG",
        "personnel": ["Alice", "Bob"],
        "constraints": {
            "num_active_teams": 1,
            "personnel_needed_per_shift": {"AM": 1, "PM": 1, "24H": 1},
            "standby_per_day": 1,
            "max_consecutive_duties": 3,
            "catch_up_limit": 0.0,
            "solver_timeout_seconds": 60.0,
        },
        "points": {
            "AM": 1.0,
            "PM": 1.0,
            "24H": 2.0,
            "S/B": 0.5,
        },
        "rules": {"transitions": {}},
    }
    p = tmp_path / "config.json"
    with open(p, "w") as f:
        json.dump(config_data, f)
    return str(p)


# --- Tests ---


def test_load_server_config(server_config_file):
    """Test Step 1: Does the app load correctly from a file?"""
    config = DataManager.load_config(filepath=server_config_file)
    assert config.year == 2026
    assert config.personnel == ["Alice", "Bob"]
    # Check Alias loading ("24H" key in JSON -> FULL_24H field)
    assert config.points.FULL_24H == 2.0


def test_memory_isolation(server_config_file):
    """
    Test Step 2: Does modifying the object in memory leave the file untouched?
    """
    # 1. Load
    config = DataManager.load_config(filepath=server_config_file)

    # 2. Modify Memory
    config.year = 2099

    # 3. Check File (Should still be 2026)
    with open(server_config_file, "r") as f:
        file_data = json.load(f)

    assert file_data["year"] == 2026
    assert config.year == 2099


def test_download_integrity(server_config_file):
    """
    Test Step 3: Does Downloaded JSON match Server Data?
    Verifies object reconstruction integrity.
    """
    # 1. Load Server Config
    server_obj = DataManager.load_config(filepath=server_config_file)

    # 2. Simulate Download (Dump to JSON string using aliases)
    json_str = server_obj.model_dump_json(by_alias=True)
    download_dict = json.loads(json_str)

    # 3. Re-import
    new_obj = AppConfig.from_dict_with_recovery(download_dict)

    # 4. Compare
    assert new_obj.year == server_obj.year
    assert new_obj.points.FULL_24H == server_obj.points.FULL_24H
    # Verify Alias usage in JSON
    assert "24H" in download_dict["points"]


def test_upload_merge_logic(server_config_file):
    """
    Test Step 4: Does uploading a partial config merge correctly?
    """
    current_state = DataManager.load_config(filepath=server_config_file)

    # User uploads a file changing ONLY the year and one constraint
    upload_payload = {"year": 2099, "constraints": {"num_active_teams": 5}}

    # Apply Merge
    new_config = AppConfig.from_dict_with_recovery(upload_payload, fallback=current_state)

    # Assert Updates
    assert new_config.year == 2099
    assert new_config.constraints.num_active_teams == 5

    # Assert Preservation (Data not in upload)
    assert new_config.personnel == ["Alice", "Bob"]
    assert new_config.country_code == "SG"
