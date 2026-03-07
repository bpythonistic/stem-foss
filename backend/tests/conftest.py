"""This file contains fixtures for testing the FastAPI application.

It sets up a test database, creates a test client, and provides a fixture for an authenticated user.
The fixtures ensure that each test runs in isolation with a clean database state.
"""

from pathlib import Path

import pytest
from yaml import safe_load

CONFIG_FILE_PATH = Path(__file__).parent / "testdata" / "testconfig.yaml"


@pytest.fixture(scope="module")
def config() -> dict:
    """
    Fixture for loading test data from a YAML file.

    :return: A dictionary containing the test data.
    :rtype: dict
    """
    with open(CONFIG_FILE_PATH, "r") as f:
        data = safe_load(f)["data"]
    return data
