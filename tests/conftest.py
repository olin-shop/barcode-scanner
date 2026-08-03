"""
Pytest configuration and global fixtures for the barcode scanner backend and GUI.
Sets up environment variables, the Quart test client, state isolation, and GUI display detection.
"""

import os
import sys
from typing import Generator

import pytest

# Inject root and src directories into sys.path so tests can import modules seamlessly
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
TESTS_DIR = os.path.join(ROOT_DIR, "tests")

for d in (SRC_DIR, ROOT_DIR, TESTS_DIR):
    if d not in sys.path:
        sys.path.insert(0, d)

from dotenv import load_dotenv

# Load real environment variables if .env exists
load_dotenv()

# Mock out environment variables so tests don't crash when running without a real .env
if "NAME_URL" not in os.environ:
    os.environ["NAME_URL"] = "http://fake-url/names"
if "ITEM_URL" not in os.environ:
    os.environ["ITEM_URL"] = "http://fake-url/items"
if "CHECKOUT_URL" not in os.environ:
    os.environ["CHECKOUT_URL"] = "http://fake-url/checkout"
if "BORROWED_ITEMS_URL" not in os.environ:
    os.environ["BORROWED_ITEMS_URL"] = "http://fake-url/borrowed-items"
if "INTRO_URL" not in os.environ:
    os.environ["INTRO_URL"] = "http://fake-url/intro-sheet"
if "ELEC_URL" not in os.environ:
    os.environ["ELEC_URL"] = "http://fake-url/303-sheet"
if "PORT" not in os.environ:
    os.environ["PORT"] = "5000"
if "HOST_IP" not in os.environ:
    os.environ["HOST_IP"] = "127.0.0.1"
if "CURRENT_API_KEY" not in os.environ:
    os.environ["CURRENT_API_KEY"] = "test_current_api_key_123"
if "OLD_API_KEY" not in os.environ:
    os.environ["OLD_API_KEY"] = "test_old_api_key_456"

from quart import Quart
from quart.testing import QuartClient
from backend.endpoints import quart_app
from backend.app_state import pending_requests


def _check_gui_available() -> bool:
    """Checks if Tkinter can initialize a window on the current OS/display environment."""
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.destroy()
        return True
    except Exception:
        return False


HAS_GUI = _check_gui_available()
requires_gui = pytest.mark.skipif(
    not HAS_GUI,
    reason="GUI display server not available in this environment (headless Linux/CI without Xvfb)",
)


@pytest.fixture
def app() -> Quart:
    """Fixture that provides the Quart application instance."""
    return quart_app


@pytest.fixture
def client(app: Quart) -> QuartClient:
    """Fixture that provides a Quart test client for making requests."""
    return app.test_client()


@pytest.fixture(autouse=True)
def clear_state() -> Generator[None, None, None]:
    """Clear any pending requests before each test to ensure complete isolation."""
    pending_requests.clear()
    yield
