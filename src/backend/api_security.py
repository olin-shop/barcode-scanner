"""
API Key rotation and security module.
Generates, stores, and loads rotating API keys for Power Automate authentication.
"""

import sys
import logging
import os
import secrets
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv, set_key

logger = logging.getLogger(__name__)

ENV_FILE = Path(__file__).parent.parent.parent / ".env"

_current_key: Optional[str] = None
_old_key: Optional[str] = None


def load_keys() -> None:
    """Loads the keys from the .env file into memory. Prompts for setup if they don't exist."""
    global _current_key, _old_key

    # Reload dotenv to ensure we have fresh values
    load_dotenv(dotenv_path=ENV_FILE)

    _current_key = os.environ.get("CURRENT_API_KEY")
    _old_key = os.environ.get("OLD_API_KEY")

    if not _current_key or not _old_key:
        _current_key = secrets.token_urlsafe(32)
        _old_key = secrets.token_urlsafe(32)
        _save_keys()

        # Non-interactive / CI test runner detection
        is_non_interactive = (
            not sys.stdin
            or not hasattr(sys.stdin, "isatty")
            or not sys.stdin.isatty()
            or "PYTEST_CURRENT_TEST" in os.environ
            or "CI" in os.environ
        )

        if is_non_interactive:
            logger.info("Created initial API keys in .env (non-interactive mode).")
            return

        # Interactive Setup Prompt
        print("\n" + "=" * 60)
        print("INITIAL API KEY GENERATED!")
        print(
            "Please copy the following key into your Excel database's KeyValue column:"
        )
        print(f"\n{_current_key}\n")
        print("=" * 60 + "\n")

        try:
            input("Press Enter once you have copied it into Excel and saved... ")
        except (EOFError, KeyboardInterrupt, OSError):
            logger.info("Created initial API keys in .env.")
            return

        logger.info("Created initial API keys in .env.")
        return


def _save_keys() -> None:
    """Saves the current and old keys to the .env file."""
    try:
        # Create file if it doesn't exist
        if not ENV_FILE.exists():
            ENV_FILE.touch()

        set_key(
            dotenv_path=ENV_FILE,
            key_to_set="CURRENT_API_KEY",
            value_to_set=_current_key,
        )
        set_key(dotenv_path=ENV_FILE, key_to_set="OLD_API_KEY", value_to_set=_old_key)

        # Update local env cache immediately
        os.environ["CURRENT_API_KEY"] = _current_key
        os.environ["OLD_API_KEY"] = _old_key
    except (OSError, ValueError, AttributeError) as e:
        logger.error("Failed to save API keys to .env: %s", e)


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


def revert_api_keys() -> None:
    """
    Reverts the current API key back to the old API key in case a rotation
    dispatch to Power Automate fails or times out.
    """
    global _current_key, _old_key
    if _old_key:
        _current_key = _old_key
        _save_keys()
        logger.warning("API keys successfully reverted to the old key.")


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
# But only if not running as main script, so we can run it standalone
if __name__ != "__main__":
    load_keys()
else:
    # Setup script mode
    logging.basicConfig(level=logging.INFO)
    load_keys()
    print("\nSetup complete. You can now run your tests or start the server.")
