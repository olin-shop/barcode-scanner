"""
Unit tests for App shell and GUI pages in src/GUI/ (app.py, ScanIDPage, BorrowedItemsPage, etc.).
"""

from datetime import datetime
import pytest
from pytest_mock import MockerFixture
import customtkinter as ctk

from tests.conftest import requires_gui
from backend.backend_types import BorrowedItem
from GUI.app import App
from GUI.ScanIDPage import ScanIDPage
from GUI.BorrowedItemsPage import BorrowedItemsPage
from GUI.BorrowPage import ConfirmBorrowPage
from GUI.ReturnPage import ConfirmReturnPage
from GUI.ConfirmationPage import FinalConfirmationPage
from GUI.TimeoutPage import SessionTimeoutPage
from GUI.LoadingPage import LoadingPage


@requires_gui
def test_app_initialization(mocker: MockerFixture) -> None:
    """Verifies App shell instantiates, registers all 7 pages, and sets default ScanIDPage."""
    app = App()
    app.withdraw()

    expected_page_names = {
        "ScanIDPage",
        "BorrowedItemsPage",
        "ConfirmBorrowPage",
        "ConfirmReturnPage",
        "FinalConfirmationPage",
        "SessionTimeoutPage",
        "LoadingPage",
    }

    assert set(app.frames.keys()) == expected_page_names
    assert app._current_page_name() == "ScanIDPage"

    app.destroy()


@requires_gui
def test_app_show_frame_and_timeout_timer(mocker: MockerFixture) -> None:
    """Verifies show_frame switches visible frame and manages session timeout timer."""
    app = App()
    app.withdraw()

    # Show BorrowedItemsPage - should start timeout job
    app.show_frame("BorrowedItemsPage")
    assert app._timeout_job is not None

    # Switch to ScanIDPage - should cancel timeout job
    app.show_frame("ScanIDPage")
    assert app._timeout_job is None

    app.destroy()


@requires_gui
def test_app_reset_session(mocker: MockerFixture) -> None:
    """Verifies reset_session resets SessionManager state and returns to ScanIDPage."""
    app = App()
    app.withdraw()

    app.session.current_user_barcode = "USER123"
    app.show_frame("BorrowedItemsPage")

    app.reset_session()

    assert app.session.current_user_barcode is None
    assert app._current_page_name() == "ScanIDPage"

    app.destroy()


@requires_gui
def test_app_display_popup(mocker: MockerFixture) -> None:
    """Verifies display_popup method invokes show_popup dialog."""
    app = App()
    app.withdraw()

    popup = app.display_popup("Test App Popup")
    assert popup is not None

    popup.destroy()
    app.destroy()


@requires_gui
def test_barcode_key_event_routing(mocker: MockerFixture) -> None:
    """Verifies keypress accumulation and barcode dispatch when Return key is pressed."""
    app = App()
    app.withdraw()

    mock_dispatch = mocker.patch.object(app, "_dispatch_barcode")

    # Simulate typing "12345" followed by Return
    for char in "12345":
        event = mocker.MagicMock(keysym=char, char=char)
        app._on_key(event)

    event_return = mocker.MagicMock(keysym="Return", char="")
    app._on_key(event_return)

    mock_dispatch.assert_called_once_with("12345")

    app.destroy()


@requires_gui
def test_dispatch_barcode_handlers(mocker: MockerFixture) -> None:
    """Verifies _dispatch_barcode routes ID scan on ScanIDPage and item scan on BorrowedItemsPage."""
    app = App()
    app.withdraw()

    mock_handle_id = mocker.patch.object(app, "_handle_id_scan")
    mock_handle_item = mocker.patch.object(app, "_handle_item_scan")

    # On ScanIDPage
    app.show_frame("ScanIDPage")
    app._dispatch_barcode("ID_BARCODE")
    mock_handle_id.assert_called_once_with("ID_BARCODE")

    # On BorrowedItemsPage
    app.show_frame("BorrowedItemsPage")
    app._dispatch_barcode("ITEM_BARCODE")
    mock_handle_item.assert_called_once_with("ITEM_BARCODE")

    app.destroy()


@requires_gui
def test_borrowed_items_page_load_and_render() -> None:
    """Verifies BorrowedItemsPage loads items and renders rows in scroll_frame."""
    app = App()
    app.withdraw()

    page: BorrowedItemsPage = app.frames["BorrowedItemsPage"]
    items = [
        BorrowedItem("Drill", "101", datetime.now()),
        BorrowedItem("Saw", "102", datetime.now()),
    ]

    page.load(items)

    assert len(page._item_barcodes) == 2
    assert page._item_barcodes["Drill"] == "101"

    app.destroy()


@requires_gui
def test_confirm_borrow_and_return_page_load() -> None:
    """Verifies load() on ConfirmBorrowPage and ConfirmReturnPage updates labels."""
    app = App()
    app.withdraw()

    borrow_page: ConfirmBorrowPage = app.frames["ConfirmBorrowPage"]
    borrow_page.load("Laser Cutter", "BC_99")
    assert borrow_page._item_name == "Laser Cutter"
    assert borrow_page._item_barcode == "BC_99"

    return_page: ConfirmReturnPage = app.frames["ConfirmReturnPage"]
    return_page.load("3D Printer", "BC_88")
    assert return_page._item_name == "3D Printer"
    assert return_page._item_barcode == "BC_88"

    app.destroy()
