"""
Edge case and stress unit tests for GUI components, app shell, and animations.
"""

import asyncio
import time
from datetime import datetime
import pytest
from pytest_mock import MockerFixture
import customtkinter as ctk

from conftest import requires_gui
from backend.backend_types import BorrowedItem
from GUI.app import App
from GUI.SelectUserPage import SelectUserPage as ScanIDPage
from GUI.BorrowedItemsPage import BorrowedItemsPage
from GUI.session_manager import SessionManager


@pytest.fixture(scope="module")
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
def test_rapid_barcode_key_stream_stress(gui_app: App, mocker: MockerFixture) -> None:
    """Stress test: rapid stream of 100 keypress events followed by Return key."""
    mock_dispatch = mocker.patch.object(gui_app, "_dispatch_barcode")

    # Simulate 5 bursts of 20 rapid keypresses ending in Return
    for burst in range(5):
        for i in range(20):
            char = str(i % 10)
            gui_app._on_key(mocker.MagicMock(keysym=char, char=char))
        gui_app._on_key(mocker.MagicMock(keysym="Return", char=""))

    assert mock_dispatch.call_count == 5


@requires_gui
def test_fast_async_response_loading_page_threshold(gui_app: App, mocker: MockerFixture) -> None:
    """Feature test: Fast responses (<150ms) do NOT show LoadingPage to prevent screen flicker."""
    mock_show_frame = mocker.patch.object(gui_app, "show_frame")

    async def fast_coro():
        return "FastResult"

    callback_results = []

    # Direct synchronous resolution test for threshold logic
    gui_app.run_async_with_loading(fast_coro(), lambda res: callback_results.append(res), threshold_ms=150)

    # Wait for future and process Tkinter event loop
    for _ in range(15):
        time.sleep(0.02)
        gui_app.update_idletasks()
        gui_app.update()
        if callback_results:
            break

    assert callback_results == ["FastResult"]
    # Verify LoadingPage was NOT shown because response completed under 150ms
    loading_calls = [c for c in mock_show_frame.call_args_list if c[0][0] == "LoadingPage"]
    assert len(loading_calls) == 0


@requires_gui
def test_loading_page_minimum_display_duration_enforced(gui_app: App, mocker: MockerFixture) -> None:
    """Feature test: When LoadingPage is shown, callback is held for min_display_ms to prevent awkward screen flicker."""
    async def slow_coro():
        await asyncio.sleep(0.1)
        return "SlowResult"

    callback_results = []
    start_t = time.time()

    # Low threshold (0ms) so LoadingPage triggers immediately, min_display_ms = 250ms
    gui_app.run_async_with_loading(
        slow_coro(),
        lambda res: callback_results.append(res),
        threshold_ms=0,
        min_display_ms=250
    )

    for _ in range(30):
        time.sleep(0.02)
        gui_app.update_idletasks()
        gui_app.update()
        if callback_results:
            break

    elapsed_ms = (time.time() - start_t) * 1000.0
    assert callback_results == ["SlowResult"]
    assert elapsed_ms >= 200  # Verified minimum display hold time enforced


@requires_gui
def test_stale_callback_discarding_on_timeout(gui_app: App) -> None:
    """Edge case: Backend response arrives after user timed out; stale response is discarded."""
    # User timed out -> app is now on SessionTimeoutPage
    gui_app.show_frame("SessionTimeoutPage")

    # Stale ID scan callback arrives
    gui_app._on_user_items_loaded([])

    # Should remain on SessionTimeoutPage, not jump to BorrowedItemsPage
    assert gui_app._current_page_name() == "SessionTimeoutPage"


from GUI.LoadingPage import LoadingPage

@requires_gui
def test_animation_safety_on_widget_destruction(gui_app: App) -> None:
    """Edge case: _animate fires on destroyed LoadingPage widget without raising TclError."""
    page = LoadingPage(gui_app)
    # Destroy page widget immediately while animation loop is pending
    page.destroy()

    # Trigger animation method explicitly post-destruction
    try:
        page._animate()
    except Exception as err:
        pytest.fail(f"_animate raised an unexpected exception on destroyed widget: {err}")


@requires_gui
def test_loading_page_rhombus_animation_translation_and_wrap(gui_app: App) -> None:
    """Verifies _animate advances rhombus coordinates rightward and wraps around on boundary exceed."""
    page = LoadingPage(gui_app)
    initial_x1 = page._shape_x
    initial_x2 = page._shape2_x

    # Run single animation frame
    page._animate()

    assert page._shape_x == initial_x1 + 2.5
    assert page._shape2_x == initial_x2 + 4.5

    # Force shapes past right canvas bound to test wrap-around logic
    page._shape_x = page.canvas_width + 500
    page._shape2_x = page.canvas_width + 500

    page._animate()

    assert page._shape_x == -page._shape_width - 10
    assert page._shape2_x == -page._shape2_length - 10
    page.destroy()


@requires_gui
def test_borrowed_items_large_dataset_rendering(gui_app: App) -> None:
    """Stress test: BorrowedItemsPage renders 120 items in scroll frame efficiently."""
    page: BorrowedItemsPage = gui_app.frames["BorrowedItemsPage"]
    large_item_list = [
        BorrowedItem(f"Equipment #{i}", f"BC_{i:04d}", datetime.now())
        for i in range(120)
    ]

    page.load(large_item_list)

    assert len(page._item_barcodes) == 120
    assert len(page.scroll_frame.winfo_children()) == 120


@pytest.mark.asyncio
async def test_session_manager_special_character_barcodes(mocker: MockerFixture) -> None:
    """Edge case: SessionManager handles non-standard barcodes with symbols and spaces."""
    sm = SessionManager()
    mocker.patch.object(sm, "_backend_lookup_item", return_value=("Oscilloscope", True))

    special_barcode = "  BC-99/A&B#100  "
    name, is_borrowed = await sm.lookup_item(special_barcode)

    assert name == "Oscilloscope"
    assert is_borrowed is True
