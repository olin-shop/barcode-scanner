"""
Unit tests for App shell and GUI pages in src/GUI/ (app.py, ScanIDPage, BorrowedItemsPage, etc.).
"""

from datetime import datetime

import pytest
from pytest_mock import MockerFixture

from conftest import requires_gui
from backend.backend_types import BorrowedItem
from GUI.app import App
from GUI.SelectUserPage import SelectUserPage as ScanIDPage
from GUI.BorrowedItemsPage import BorrowedItemsPage
from GUI.BorrowPage import ConfirmBorrowPage
from GUI.ReturnPage import ConfirmReturnPage


@pytest.fixture
def gui_app():
    """Provides a hidden App instance and handles clean teardown."""
    try:
        app = App()
    except Exception:
        import time

        time.sleep(0.1)
        app = App()
    app.withdraw()
    yield app
    try:
        app.update_idletasks()
        app.destroy()
    except Exception:
        pass


@requires_gui
def test_app_initialization(gui_app: App) -> None:
    """Verifies App shell instantiates, registers all pages, and sets default HomePage."""
    expected_page_names = {
        "HomePage",
        "SelectUserPage",
        "BorrowedItemsPage",
        "ConfirmBorrowPage",
        "ConfirmReturnPage",
        "FinalConfirmationPage",
        "SessionTimeoutPage",
        "LoadingPage",
        "InvalidUserPage",
        "InvalidItemIDPage",
        "InvalidItemPage",
    }

    assert set(gui_app.frames.keys()) == expected_page_names
    assert gui_app._current_page_name() == "HomePage"


@requires_gui
def test_app_show_frame_and_timeout_timer(gui_app: App) -> None:
    """Verifies show_frame switches visible frame and manages session timeout timer."""
    # Show BorrowedItemsPage - should start timeout job
    gui_app.show_frame("BorrowedItemsPage")
    assert gui_app._timeout_job is not None

    # Switch to SessionTimeoutPage - should cancel timeout job
    gui_app.show_frame("SessionTimeoutPage")
    assert gui_app._timeout_job is None


@requires_gui
def test_app_reset_session(gui_app: App) -> None:
    """Verifies reset_session resets SessionManager state and returns to HomePage."""
    gui_app.session.current_user_barcode = "USER123"
    gui_app.show_frame("BorrowedItemsPage")

    gui_app.reset_session()

    assert gui_app.session.current_user_barcode is None
    assert gui_app._current_page_name() == "HomePage"


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
    """Verifies _dispatch_barcode routes ID scan on SelectUserPage and item scan on BorrowedItemsPage."""
    mock_handle_id = mocker.patch.object(gui_app, "_handle_id_scan")
    mock_handle_item = mocker.patch.object(gui_app, "_handle_item_scan")

    # On SelectUserPage
    gui_app.show_frame("SelectUserPage")
    gui_app._dispatch_barcode("ID_BARCODE")
    mock_handle_id.assert_called_once_with("ID_BARCODE")

    # On BorrowedItemsPage
    gui_app.show_frame("BorrowedItemsPage")
    gui_app._dispatch_barcode("ITEM_BARCODE")
    mock_handle_item.assert_called_once_with("ITEM_BARCODE")


@requires_gui
def test_borrowed_items_page_load_and_render(gui_app: App) -> None:
    """Verifies BorrowedItemsPage loads items, renders rows, and manages user name label."""
    page: BorrowedItemsPage = gui_app.frames["BorrowedItemsPage"]
    items = [
        BorrowedItem("Drill", "101", datetime.now()),
        BorrowedItem("Saw", "102", datetime.now()),
    ]

    # Test explicit user_name passed to load
    page.load(items, user_name="Jane Doe")
    assert len(page._item_barcodes) == 2
    assert page._item_barcodes["Drill"] == "101"
    assert page.user_name_label.cget("text") == "Jane Doe"

    # Test implicit user_name resolution from session
    gui_app.session.current_user_name = "Alex Morgan"
    page.load(items)
    assert page.user_name_label.cget("text") == "Alex Morgan"

    # Test fallback to empty string when no user name is present
    gui_app.session.current_user_name = ""
    page.load(items)
    assert page.user_name_label.cget("text") == ""


@requires_gui
def test_on_user_items_loaded_dispatches_user_name(gui_app: App) -> None:
    """Verifies _on_user_items_loaded passes session.current_user_name to BorrowedItemsPage."""
    gui_app.session.current_user_name = "Sam Taylor"
    items = [BorrowedItem("Multimeter", "201", datetime.now())]

    gui_app._on_user_items_loaded(items)

    page: BorrowedItemsPage = gui_app.frames["BorrowedItemsPage"]
    assert gui_app._current_page_name() == "BorrowedItemsPage"
    assert page.user_name_label.cget("text") == "Sam Taylor"


@requires_gui
def test_loading_page_dual_rhombus_canvas_initialization(gui_app: App) -> None:
    """Verifies LoadingPage initializes dual rhombus canvas properties and shape structures."""
    from GUI.LoadingPage import LoadingPage

    page: LoadingPage = gui_app.frames["LoadingPage"]

    assert page.canvas_width > 0
    assert page.canvas_height == 30
    assert page._shape_width == 400
    assert page._shape2_length == 600
    assert page._shape2_height == 7.5


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


@requires_gui
def test_on_item_looked_up_already_borrowed(
    gui_app: App, mocker: MockerFixture
) -> None:
    """Verifies an already borrowed item (is_borrowed=None) shows a popup and stays on current page."""
    mock_popup = mocker.patch("GUI.app.show_popup")
    gui_app.show_frame("BorrowedItemsPage")

    gui_app._on_item_looked_up(("Saw", None), "12345")

    mock_popup.assert_called_once()
    assert "already borrowed" in mock_popup.call_args[0][0].lower()
    assert gui_app._current_page_name() == "BorrowedItemsPage"


@requires_gui
def test_on_item_looked_up_already_borrowed_empty_name(
    gui_app: App, mocker: MockerFixture
) -> None:
    """Verifies an already borrowed item with empty name shows popup and does NOT show InvalidItemPage."""
    mock_popup = mocker.patch("GUI.app.show_popup")
    mock_invalid = mocker.patch.object(gui_app, "show_invalid_item_page")
    gui_app.show_frame("BorrowedItemsPage")

    gui_app._on_item_looked_up(("", None), "12345")

    mock_popup.assert_called_once()
    mock_invalid.assert_not_called()
    assert "already borrowed" in mock_popup.call_args[0][0].lower()
    assert gui_app._current_page_name() == "BorrowedItemsPage"


@requires_gui
def test_select_user_page_search_and_selection(
    gui_app: App, mocker: MockerFixture
) -> None:
    """Verifies search entry filters list, selecting student enables Next button, and clicking Next starts session."""
    from backend.student_roster import roster, StudentRecord

    roster.students = [StudentRecord("Charlie Brown", "cbrown@olin.edu")]

    mocker.patch.object(gui_app, "_handle_id_scan")
    select_page = gui_app.frames["SelectUserPage"]
    select_page.load_students()

    assert select_page.next_button.cget("state") == "disabled"

    # Type query to filter
    select_page.search_entry.insert(0, "Charlie")
    select_page._on_type_search()

    assert len(select_page._filtered_students) == 1
    assert select_page._filtered_students[0].name == "Charlie Brown"

    # Select student from dropdown
    select_page._select_student(select_page._filtered_students[0])
    assert select_page.next_button.cget("state") == "normal"
    assert select_page.search_entry.get() == "Charlie Brown"

    # Click Next
    select_page._on_next_clicked()
    assert gui_app.session.current_user_name == "Charlie Brown"
    gui_app._handle_id_scan.assert_called_once_with("cbrown@olin.edu")


@requires_gui
def test_select_user_page_home_button(gui_app: App) -> None:
    """Verifies clicking Home button on SelectUserPage resets session and returns to HomePage."""
    gui_app.show_frame("SelectUserPage")
    assert gui_app._current_page_name() == "SelectUserPage"

    select_page = gui_app.frames["SelectUserPage"]
    select_page._on_home_clicked()

    assert gui_app._current_page_name() == "HomePage"


@requires_gui
def test_borrowed_items_page_home_button(gui_app: App) -> None:
    """Verifies clicking Home button on BorrowedItemsPage resets session and returns to HomePage."""
    gui_app.session.current_user_name = "Alice Smith"
    gui_app.show_frame("BorrowedItemsPage")
    assert gui_app._current_page_name() == "BorrowedItemsPage"

    borrowed_page = gui_app.frames["BorrowedItemsPage"]
    borrowed_page._on_home_clicked()

    assert gui_app.session.current_user_name == ""
    assert gui_app._current_page_name() == "HomePage"
