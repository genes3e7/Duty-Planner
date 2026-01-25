"""
tests/test_config_workflow.py

Tests the full lifecycle of the configuration:
1. Server Initialization (File -> Memory)
2. In-Memory Isolation (Memory != File)
3. Download (Memory -> JSON)
4. Upload (JSON -> Memory, with merging)
"""

import json

import pytest

from app.core.data import DataManager
from app.models.config import AppConfig

# --- Fixtures ---


@pytest.fixture
def server_config_file(tmp_path):
    """
    Creates a temporary 'server-side' config.json file.
    Returns the file path.
    """
    config_data = {
        "year": 2026,
        "month": 5,
        "country_code": "SG",
        "personnel": ["Alice", "Bob"],
        "constraints": {
            "num_active_teams": 1,
            "num_standby_teams": 1,
            "personnel_needed_per_shift": {"AM": 1, "PM": 1, "24H": 1},
            "standby_per_day": 1,
            "max_consecutive_duties": 3,
            "catch_up_limit": 0.0,
            "solver_timeout_seconds": 60.0,
        },
        "points": {
            "AM": 1.0,
            "PM": 1.0,
            "24H": 2.0,  # Alias expected by loader
            "S/B": 0.5,  # Alias expected by loader
            "ph_multiplier": 2.0,
            "ph_eve_am_multiplier": 1.5,
            "ph_eve_pm_multiplier": 1.5,
            "ph_eve_24h_multiplier": 1.5,
            "weekend_multiplier": 1.5,
            "friday_am_multiplier": 1.0,
            "friday_pm_multiplier": 1.0,
            "friday_24h_multiplier": 1.0,
            "ph_is_multiplier": True,
            "ph_eve_am_is_multiplier": True,
            "ph_eve_pm_is_multiplier": True,
            "ph_eve_24h_is_multiplier": True,
            "weekend_is_multiplier": True,
            "friday_am_is_multiplier": True,
            "friday_pm_is_multiplier": True,
            "friday_24h_is_multiplier": True,
        },
        "rules": {
            "transitions": {
                "AM": {"AM": "Allowed", "PM": "Soft Ban", "24H": "Allowed", "S/B": "Allowed"},
                "PM": {"AM": "Hard Ban", "PM": "Hard Ban", "24H": "Hard Ban", "S/B": "Soft Ban"},
                "24H": {"AM": "Hard Ban", "PM": "Allowed", "24H": "Hard Ban", "S/B": "Hard Ban"},
                "S/B": {"AM": "Soft Ban", "PM": "Allowed", "24H": "Hard Ban", "S/B": "Soft Ban"},
            }
        },
    }

    file_path = tmp_path / "config.json"
    with open(file_path, "w") as f:
        json.dump(config_data, f)

    return str(file_path)


@pytest.fixture
def sample_upload_json():
    """
    Returns a JSON string simulating a user-uploaded config file.
    Contains CHANGES (Year 2027) and NEW FIELDS (num_active_teams=3).
    """
    return json.dumps(
        {
            "year": 2027,
            "month": 12,
            "constraints": {
                "num_active_teams": 3,  # Changed value
                "standby_per_day": 5,  # Changed value
            },
            "points": {
                "S/B": 10.0  # Changed value (using Alias)
            },
        }
    )


# --- Tests ---


def test_load_server_config(server_config_file):
    """
    Test Step 1: Does the app load correctly from a file?
    """
    config = DataManager.load_config(filepath=server_config_file)

    assert config.year == 2026
    assert config.personnel == ["Alice", "Bob"]
    assert config.constraints.num_active_teams == 1
    # Check that the alias "24H" (2.0) was mapped to field FULL_24H
    assert config.points.FULL_24H == 2.0


def test_memory_isolation(server_config_file):
    """
    Test Step 2: Does modifying the object in memory leave the file untouched?
    """
    # 1. Load
    config = DataManager.load_config(filepath=server_config_file)

    # 2. Modify Memory
    config.year = 2099
    config.constraints.num_active_teams = 99

    # 3. Check File (Should still be 2026)
    with open(server_config_file, "r") as f:
        file_data = json.load(f)

    assert file_data["year"] == 2026
    assert file_data["constraints"]["num_active_teams"] == 1
    assert config.year == 2099


def test_download_integrity(server_config_file):
    """
    Test Step 3: Does the Downloaded JSON contain the same data as the Server File?

    We compare the *objects* created from both sources.
    This handles the case where Server File uses Aliases ("S/B") but
    Download uses Field Names ("SB") OR Aliases depending on configuration.
    """
    # 1. Load from Server File -> Object
    server_config_obj = DataManager.load_config(filepath=server_config_file)

    # 2. Simulate Download (Generate JSON string from Object)
    # Using by_alias=True to ensure compatibility with uploader
    downloaded_json_str = server_config_obj.model_dump_json(by_alias=True)
    downloaded_dict = json.loads(downloaded_json_str)

    # 3. Load Downloaded JSON -> Object
    downloaded_config_obj = AppConfig.from_dict_with_recovery(downloaded_dict)

    # 4. Compare Objects
    assert downloaded_config_obj.year == server_config_obj.year
    assert downloaded_config_obj.constraints.num_active_teams == server_config_obj.constraints.num_active_teams
    assert downloaded_config_obj.points.SB == server_config_obj.points.SB
    assert downloaded_config_obj.points.FULL_24H == server_config_obj.points.FULL_24H


def test_upload_merges_correctly(server_config_file, sample_upload_json):
    """
    Test Step 4: Does memory load correctly from uploaded config.json?
    Verifies that uploaded values overwrite existing ones, but missing values
    in upload are preserved (Fallback/Merge behavior).
    """
    # 1. Initial State
    current_state = DataManager.load_config(filepath=server_config_file)
    assert current_state.year == 2026
    assert current_state.points.SB == 0.5

    # 2. Simulate Upload
    uploaded_dict = json.loads(sample_upload_json)

    # 3. Apply Update
    new_config = AppConfig.from_dict_with_recovery(uploaded_dict, fallback=current_state)

    # Assert UPDATED values
    assert new_config.year == 2027
    assert new_config.constraints.num_active_teams == 3
    assert new_config.points.SB == 10.0  # Loaded successfully from "S/B"

    # Assert PRESERVED values (Not in upload)
    assert new_config.country_code == "SG"
    assert new_config.personnel == ["Alice", "Bob"]
