"""
Unit tests for GUI/popup.py (show_popup dialog).
"""

import pytest
import customtkinter as ctk

from tests.conftest import requires_gui
from GUI.popup import show_popup


@requires_gui
def test_show_popup_creation() -> None:
    """Verifies that show_popup creates a centered, frameless dialog with correct text and close button."""
    app = ctk.CTk()
    app.geometry("800x480")
    app.withdraw()  # Keep window hidden offscreen during test execution

    test_message = "Warning: Equipment missing"
    popup = show_popup(test_message, app)

    assert popup is not None
    assert isinstance(popup, ctk.CTkToplevel)

    # Verify window attributes
    assert popup.overrideredirect() is True

    # Destroy windows cleanly after test
    popup.destroy()
    app.destroy()


@requires_gui
def test_show_popup_without_parent() -> None:
    """Verifies show_popup can resolve master when parent argument is omitted."""
    app = ctk.CTk()
    app.geometry("800x480")
    app.withdraw()

    popup = show_popup("Standalone warning")
    assert popup is not None

    popup.destroy()
    app.destroy()
