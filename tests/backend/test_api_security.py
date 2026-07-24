"""
Unit tests for the api_security.py module.
"""

import os
import pytest
from pathlib import Path
from dotenv import dotenv_values
from backend import api_security


@pytest.fixture(autouse=True)
def setup_teardown_api_keys(tmp_path, monkeypatch):
    """
    Fixture to isolate the .env file to a temporary directory
    so we don't overwrite the real keys during testing.
    """
    test_env_file = tmp_path / ".env"
    monkeypatch.setattr(api_security, "ENV_FILE", test_env_file)

    # Mock input to prevent hanging
    monkeypatch.setattr("builtins.input", lambda _: None)

    # Remove from environment to simulate fresh start
    if "CURRENT_API_KEY" in os.environ:
        del os.environ["CURRENT_API_KEY"]
    if "OLD_API_KEY" in os.environ:
        del os.environ["OLD_API_KEY"]

    # Reset state
    api_security._current_key = None
    api_security._old_key = None

    yield

    # Cleanup state
    api_security._current_key = None
    api_security._old_key = None
    if "CURRENT_API_KEY" in os.environ:
        del os.environ["CURRENT_API_KEY"]
    if "OLD_API_KEY" in os.environ:
        del os.environ["OLD_API_KEY"]


def test_initial_generation():
    """Test that keys are generated securely on the first run when the file doesn't exist."""
    assert not api_security.ENV_FILE.exists()

    # Calling get_current_key() should trigger load_keys() and generation
    current_key = api_security.get_current_key()
    old_key = api_security.get_old_key()

    assert current_key is not None
    assert old_key is not None
    assert len(current_key) > 20
    assert len(old_key) > 20

    # Verify file was created and contains keys
    assert api_security.ENV_FILE.exists()
    env_data = dotenv_values(api_security.ENV_FILE)
    assert env_data.get("CURRENT_API_KEY") == current_key
    assert env_data.get("OLD_API_KEY") == old_key


def test_rotation():
    """Test that rotating keys shifts the current key to the old key and generates a new one."""
    initial_current = api_security.get_current_key()

    api_security.rotate_api_keys()

    new_current = api_security.get_current_key()
    new_old = api_security.get_old_key()

    assert new_current != initial_current
    assert new_old == initial_current

    # Verify it saved to disk
    env_data = dotenv_values(api_security.ENV_FILE)
    assert env_data.get("CURRENT_API_KEY") == new_current
    assert env_data.get("OLD_API_KEY") == new_old


def test_fallback_on_missing_keys():
    """Test that missing keys in the .env file generate new keys."""
    # Write empty .env
    api_security.ENV_FILE.touch()

    api_security.load_keys()

    assert api_security.get_current_key() is not None
    assert api_security.get_old_key() is not None
