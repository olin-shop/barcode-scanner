"""
API Key rotation and security module.
Generates, stores, and loads rotating API keys for Power Automate authentication.

The kiosk keeps three kinds of key:
- current: sent with every outgoing request.
- old: the key before the last rotation, still accepted on incoming callbacks.
- pending: keys from a rotation whose outcome was never confirmed. Power Automate
  may or may not hold one of them, so they are accepted on callbacks and kept until
  requests.resolve_pending_keys() learns which key Power Automate actually has.
  A pending key is never thrown away unconfirmed, because losing the key Power
  Automate holds would lock the kiosk out until someone resets it by hand.
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
_pending_keys: list[str] = []


def _parse_pending(raw: Optional[str]) -> list[str]:
    """Parses the comma-separated PENDING_API_KEYS value (keys are URL-safe, no commas)."""
    return [k.strip() for k in (raw or "").split(",") if k.strip()]


def load_keys() -> None:
    """Loads the keys from the .env file into memory. Prompts for setup if they don't exist."""
    global _current_key, _old_key, _pending_keys

    # Reload dotenv to ensure we have fresh values
    load_dotenv(dotenv_path=ENV_FILE)

    _current_key = os.environ.get("CURRENT_API_KEY")
    _old_key = os.environ.get("OLD_API_KEY")
    _pending_keys = _parse_pending(os.environ.get("PENDING_API_KEYS"))

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
        pending_value = ",".join(_pending_keys)
        set_key(
            dotenv_path=ENV_FILE,
            key_to_set="PENDING_API_KEYS",
            value_to_set=pending_value,
        )

        # Update local env cache immediately
        os.environ["CURRENT_API_KEY"] = _current_key
        os.environ["OLD_API_KEY"] = _old_key
        os.environ["PENDING_API_KEYS"] = pending_value
    except (OSError, ValueError, AttributeError, TypeError) as e:
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
    Goes back to the old key after a rotation whose outcome is unknown.

    The unconfirmed new key is kept as a pending key instead of being discarded:
    Power Automate may already have saved it, and throwing it away would lock the
    kiosk out. resolve_pending_keys() later confirms or discards it.
    """
    global _current_key, _pending_keys
    if not _old_key or _current_key == _old_key:
        return
    if _current_key and _current_key not in _pending_keys:
        _pending_keys = [*_pending_keys, _current_key]
    _current_key = _old_key
    _save_keys()
    logger.warning(
        "API keys reverted to the old key; the unconfirmed new key is kept as pending "
        "until Power Automate confirms which one it holds."
    )


def abandon_rotation() -> None:
    """
    Goes back to the old key after Power Automate confirmed it still holds the old key,
    so the new key can be dropped safely.
    """
    global _current_key
    if not _old_key or _current_key == _old_key:
        return
    _current_key = _old_key
    _save_keys()
    logger.warning("Power Automate kept the old API key; rotation undone.")


def get_pending_keys() -> list[str]:
    """Returns unconfirmed keys from an earlier rotation (empty when none)."""
    if _current_key is None:
        load_keys()
    return list(_pending_keys)


def confirm_pending_key(key: str) -> None:
    """
    Makes a pending key current once Power Automate has accepted it.
    The previous current key becomes the old key; other pending keys are dropped,
    since Power Automate holds exactly one key.
    """
    global _current_key, _old_key, _pending_keys
    if key not in _pending_keys:
        return
    _old_key = _current_key
    _current_key = key
    _pending_keys = []
    _save_keys()
    logger.warning("Confirmed a pending API key with Power Automate; it is now current.")


def discard_pending_keys() -> None:
    """Drops pending keys once Power Automate has confirmed it still holds the current key."""
    global _pending_keys
    if not _pending_keys:
        return
    _pending_keys = []
    _save_keys()
    logger.info("Power Automate holds the current API key; pending keys discarded.")


def accepted_keys() -> set[str]:
    """Keys accepted on incoming callbacks: current, old, and any pending keys."""
    keys = {get_current_key(), get_old_key(), *get_pending_keys()}
    return {k for k in keys if k}


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
