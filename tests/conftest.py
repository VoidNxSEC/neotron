"""
Pytest configuration and fixtures for neotron compliance tests.
"""

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def test_data_dir():
    """Return path to test data directory"""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def temporal_address():
    """Temporal server address for tests"""
    return os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
