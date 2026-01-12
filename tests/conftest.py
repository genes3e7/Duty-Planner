"""
tests/conftest.py

Shared Pytest configuration and fixtures.
Provides common objects like default AppConfig and mock data for tests.
"""

import os
import sys

import pytest

# Ensure 'app' module is importable from tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.config import AppConfig


@pytest.fixture
def default_config() -> AppConfig:
    """
    Fixture providing a default AppConfig instance.
    Useful for tests needing a standard configuration state.

    Returns:
        AppConfig: A fresh configuration object with default values.
    """
    return AppConfig.default()
