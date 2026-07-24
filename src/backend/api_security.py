"""
API Key rotation and security module.
Generates, stores, and loads rotating API keys for Power Automate authentication.
"""

import json
import logging
import secrets
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

KEYS_FILE = Path(__file__).parent / "api_keys.json"

_current_key: Optional[str] = None
_old_key: Optional[str] = None

def load_keys() -> None:
    """Loads the keys from the JSON file into memory. Creates the file if it doesn't exist."""
    global _current_key, _old_key
    if not KEYS_FILE.exists():
        _current_key = secrets.token_urlsafe(32)
        _old_key = secrets.token_urlsafe(32)
        _save_keys()
        logger.info("Created initial api_keys.json with secure random keys.")
        return

    try:
        with open(KEYS_FILE, "r") as f:
            data = json.load(f)
            _current_key = data.get("current_key") or secrets.token_urlsafe(32)
            _old_key = data.get("old_key") or secrets.token_urlsafe(32)
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Failed to load api_keys.json: %s. Generating new secure keys.", e)
        _current_key = secrets.token_urlsafe(32)
        _old_key = secrets.token_urlsafe(32)


def _save_keys() -> None:
    """Saves the current and old keys to the JSON file."""
    try:
        with open(KEYS_FILE, "w") as f:
            json.dump({
                "current_key": _current_key,
                "old_key": _old_key
            }, f, indent=4)
    except IOError as e:
        logger.error("Failed to save api_keys.json: %s", e)


def rotate_api_keys() -> None:
    """
    Generates a new secure random API key, rotates the current key to old, 
    and saves to disk.
    """
    global _current_key, _old_key
    _old_key = _current_key
    _current_key = secrets.token_urlsafe(32)
    _save_keys()
    logger.info("API keys successfully rotated.")


def get_current_key() -> str:
    """Returns the current valid API key."""
    if _current_key is None:
        load_keys()
    return _current_key or secrets.token_urlsafe(32)


def get_old_key() -> str:
    """Returns the previously valid API key."""
    if _old_key is None:
        load_keys()
    return _old_key or secrets.token_urlsafe(32)

# Ensure keys are loaded when module is imported
load_keys()
