"""
Unit tests for App shell and GUI pages in src/GUI/ (app.py, ScanIDPage, BorrowedItemsPage, etc.).
"""

from datetime import datetime
import pytest
from pytest_mock import MockerFixture
import customtkinter as ctk

from conftest import requires_gui
from backend.backend_types import BorrowedItem
from GUI.app import App
from GUI.ScanIDPage import ScanIDPage
from GUI.BorrowedItemsPage import BorrowedItemsPage
from GUI.BorrowPage import ConfirmBorrowPage
from GUI.ReturnPage import ConfirmReturnPage


@pytest.fixture
def gui_app():
    """Provides a hidden App instance and handles clean teardown."""
    app = App()
    app.withdraw()
    yield app
    try:
        app.destroy()
    except Exception:
        pass


@requires_gui
def test_app_initialization(gui_app: App) -> None:
    """Verifies App shell instantiates, registers all 7 pages, and sets default ScanIDPage."""
    expected_page_names = {
        "ScanIDPage",
        "BorrowedItemsPage",
        "ConfirmBorrowPage",
        "ConfirmReturnPage",
        "FinalConfirmationPage",
        "SessionTimeoutPage",
        "LoadingPage",
    }

    assert set(gui_app.frames.keys()) == expected_page_names
    assert gui_app._current_page_name() == "ScanIDPage"


@requires_gui
def test_app_show_frame_and_timeout_timer(gui_app: App) -> None:
    """Verifies show_frame switches visible frame and manages session timeout timer."""
    # Show BorrowedItemsPage - should start timeout job
    gui_app.show_frame("BorrowedItemsPage")
    assert gui_app._timeout_job is not None

    # Switch to ScanIDPage - should cancel timeout job
    gui_app.show_frame("ScanIDPage")
    assert gui_app._timeout_job is None


@requires_gui
def test_app_reset_session(gui_app: App) -> None:
    """Verifies reset_session resets SessionManager state and returns to ScanIDPage."""
    gui_app.session.current_user_barcode = "USER123"
    gui_app.show_frame("BorrowedItemsPage")

    gui_app.reset_session()

    assert gui_app.session.current_user_barcode is None
    assert gui_app._current_page_name() == "ScanIDPage"


@requires_gui
def test_app_display_popup(gui_app: App) -> None:
    """Verifies display_popup method invokes show_popup dialog."""
    popup = gui_app.display_popup("Test App Popup")
    assert popup is not None
    popup.destroy()


@requires_gui
def test_barcode_key_event_routing(gui_app: App, mocker: MockerFixture) -> None:
    """Verifies keypress accumulation and barcode dispatch when Return key is pressed."""
    mock_dispatch = mocker.patch.object(gui_app, "_dispatch_barcode")

    # Simulate typing "12345" followed by Return
    for char in "12345":
        event = mocker.MagicMock(keysym=char, char=char)
        gui_app._on_key(event)

    event_return = mocker.MagicMock(keysym="Return", char="")
    gui_app._on_key(event_return)

    mock_dispatch.assert_called_once_with("12345")


@requires_gui
def test_dispatch_barcode_handlers(gui_app: App, mocker: MockerFixture) -> None:
    """Verifies _dispatch_barcode routes ID scan on ScanIDPage and item scan on BorrowedItemsPage."""
    mock_handle_id = mocker.patch.object(gui_app, "_handle_id_scan")
    mock_handle_item = mocker.patch.object(gui_app, "_handle_item_scan")

    # On ScanIDPage
    gui_app.show_frame("ScanIDPage")
    gui_app._dispatch_barcode("ID_BARCODE")
    mock_handle_id.assert_called_once_with("ID_BARCODE")

    # On BorrowedItemsPage
    gui_app.show_frame("BorrowedItemsPage")
    gui_app._dispatch_barcode("ITEM_BARCODE")
    mock_handle_item.assert_called_once_with("ITEM_BARCODE")


@requires_gui
def test_borrowed_items_page_load_and_render(gui_app: App) -> None:
    """Verifies BorrowedItemsPage loads items and renders rows in scroll_frame."""
    page: BorrowedItemsPage = gui_app.frames["BorrowedItemsPage"]
    items = [
        BorrowedItem("Drill", "101", datetime.now()),
        BorrowedItem("Saw", "102", datetime.now()),
    ]

    page.load(items)

    assert len(page._item_barcodes) == 2
    assert page._item_barcodes["Drill"] == "101"


@requires_gui
def test_confirm_borrow_and_return_page_load(gui_app: App) -> None:
    """Verifies load() on ConfirmBorrowPage and ConfirmReturnPage updates labels."""
    borrow_page: ConfirmBorrowPage = gui_app.frames["ConfirmBorrowPage"]
    borrow_page.load("Laser Cutter", "BC_99")
    assert borrow_page._item_name == "Laser Cutter"
    assert borrow_page._item_barcode == "BC_99"

    return_page: ConfirmReturnPage = gui_app.frames["ConfirmReturnPage"]
    return_page.load("3D Printer", "BC_88")
    assert return_page._item_name == "3D Printer"
    assert return_page._item_barcode == "BC_88"
