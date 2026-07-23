"""
Unit tests for GUI/session_manager.py (SessionManager).
Verifies user session state lifecycle, barcode item lookups, and borrow/return/missing logic.
"""

from datetime import datetime
import pytest
from pytest_mock import MockerFixture

from backend.backend_types import BorrowedItem, Status
from GUI.session_manager import SessionManager


def test_session_manager_init() -> None:
    """Verifies default state initialization."""
    sm = SessionManager()
    assert sm.current_user_barcode is None
    assert sm.current_user_name == ""
    assert sm.current_user_email == ""
    assert sm.user_items == []


def test_session_manager_reset() -> None:
    """Verifies reset() clears all active session attributes."""
    sm = SessionManager()
    sm.current_user_barcode = "12345"
    sm.current_user_name = "Alice"
    sm.current_user_email = "alice@example.com"
    sm.user_items = [BorrowedItem("Drill", "999", datetime.now())]

    sm.reset()

    assert sm.current_user_barcode is None
    assert sm.current_user_name == ""
    assert sm.current_user_email == ""
    assert sm.user_items == []


@pytest.mark.asyncio
async def test_start_session(mocker: MockerFixture) -> None:
    """Verifies starting a session fetches and populates user items."""
    sm = SessionManager()
    mock_items = [BorrowedItem("Lathe", "555", datetime.now())]
    mocker.patch.object(sm, "_backend_get_user_items", return_value=mock_items)

    result = await sm.start_session("USER_BARCODE_1")

    assert sm.current_user_barcode == "USER_BARCODE_1"
    assert sm.user_items == mock_items
    assert result == mock_items


@pytest.mark.asyncio
async def test_lookup_item_cached_fast_path() -> None:
    """Verifies item lookup hits cached session items first without round-tripping to backend."""
    sm = SessionManager()
    item = BorrowedItem("Screwdriver", "BC123", datetime.now())
    sm.user_items = [item]

    name, is_borrowed = await sm.lookup_item("BC123")

    assert name == "Screwdriver"
    assert is_borrowed is True


@pytest.mark.asyncio
async def test_lookup_item_backend_path(mocker: MockerFixture) -> None:
    """Verifies uncached item barcode delegates to _backend_lookup_item."""
    sm = SessionManager()
    mocker.patch.object(sm, "_backend_lookup_item", return_value=("Hammer", False))

    name, is_borrowed = await sm.lookup_item("BC999")

    assert name == "Hammer"
    assert is_borrowed is False


@pytest.mark.asyncio
async def test_confirm_borrow_success(mocker: MockerFixture) -> None:
    """Verifies confirming borrow appends new item to user_items when backend succeeds."""
    sm = SessionManager()
    sm.current_user_barcode = "USER_1"
    mocker.patch.object(sm, "_backend_confirm_borrow", return_value=True)

    success = await sm.confirm_borrow("ITEM_100", "Saw")

    assert success is True
    assert len(sm.user_items) == 1
    assert sm.user_items[0].name == "Saw"
    assert sm.user_items[0].barcode == "ITEM_100"


@pytest.mark.asyncio
async def test_confirm_borrow_failure(mocker: MockerFixture) -> None:
    """Verifies confirming borrow does not mutate state when backend fails."""
    sm = SessionManager()
    mocker.patch.object(sm, "_backend_confirm_borrow", return_value=False)

    success = await sm.confirm_borrow("ITEM_100", "Saw")

    assert success is False
    assert len(sm.user_items) == 0


@pytest.mark.asyncio
async def test_confirm_return_success(mocker: MockerFixture) -> None:
    """Verifies confirming return drops item from user_items when backend succeeds."""
    sm = SessionManager()
    item1 = BorrowedItem("Item A", "BC1", datetime.now())
    item2 = BorrowedItem("Item B", "BC2", datetime.now())
    sm.user_items = [item1, item2]

    mocker.patch.object(sm, "_backend_confirm_return", return_value=True)

    success = await sm.confirm_return("BC1", "Item A")

    assert success is True
    assert len(sm.user_items) == 1
    assert sm.user_items[0].name == "Item B"


@pytest.mark.asyncio
async def test_mark_missing_success(mocker: MockerFixture) -> None:
    """Verifies marking missing drops item from user_items when backend succeeds."""
    sm = SessionManager()
    item1 = BorrowedItem("Item A", "BC1", datetime.now())
    sm.user_items = [item1]

    mocker.patch.object(sm, "_backend_mark_missing", return_value=True)

    success = await sm.mark_missing("BC1", "Item A")

    assert success is True
    assert len(sm.user_items) == 0
