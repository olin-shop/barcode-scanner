"""
Unit tests for the api_security.py module.
"""
import os
import json
import pytest
from pathlib import Path
from backend import api_security

@pytest.fixture(autouse=True)
def setup_teardown_api_keys(tmp_path, monkeypatch):
    """
    Fixture to isolate api_keys.json to a temporary directory
    so we don't overwrite the real keys during testing.
    """
    test_keys_file = tmp_path / "test_api_keys.json"
    monkeypatch.setattr(api_security, "KEYS_FILE", test_keys_file)
    
    # Reset state
    api_security._current_key = None
    api_security._old_key = None
    
    yield
    
    # Cleanup state
    api_security._current_key = None
    api_security._old_key = None


def test_initial_generation():
    """Test that keys are generated securely on the first run when the file doesn't exist."""
    assert not api_security.KEYS_FILE.exists()
    
    # Calling get_current_key() should trigger load_keys() and generation
    current_key = api_security.get_current_key()
    old_key = api_security.get_old_key()
    
    assert current_key is not None
    assert old_key is not None
    assert len(current_key) > 20
    assert len(old_key) > 20
    
    # Verify file was created and contains keys
    assert api_security.KEYS_FILE.exists()
    with open(api_security.KEYS_FILE, "r") as f:
        data = json.load(f)
        assert data["current_key"] == current_key
        assert data["old_key"] == old_key


def test_rotation():
    """Test that rotating keys shifts the current key to the old key and generates a new one."""
    initial_current = api_security.get_current_key()
    
    api_security.rotate_api_keys()
    
    new_current = api_security.get_current_key()
    new_old = api_security.get_old_key()
    
    assert new_current != initial_current
    assert new_old == initial_current
    
    # Verify it saved to disk
    with open(api_security.KEYS_FILE, "r") as f:
        data = json.load(f)
        assert data["current_key"] == new_current
        assert data["old_key"] == new_old


def test_fallback_on_corrupt_file():
    """Test that corrupt JSON files are handled gracefully by generating new keys."""
    # Write corrupt JSON
    with open(api_security.KEYS_FILE, "w") as f:
        f.write("{ invalid json")
        
    api_security.load_keys()
    
    assert api_security.get_current_key() is not None
    assert api_security.get_old_key() is not None
