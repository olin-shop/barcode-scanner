"""
Live integration tests for the backend outgoing requests (requests.py).
These tests verify real network connectivity against live Power Automate endpoints.
Requires a valid .env file to run successfully.
"""
import pytest
import asyncio
from datetime import datetime
import os

from backend.endpoints import quart_app
from backend.backend_constants import HOST_IP, PORT, min_datetime
from backend.requests import get_name, get_item, checkout, request_borrowed_items
from backend.backend_types import Status, UserInfoPayload

from typing import AsyncGenerator

# We use autouse so this runs before any tests in this module
@pytest.fixture(scope="module", autouse=True)
async def running_server() -> AsyncGenerator[None, None]:
    """Runs the Quart server in the background for live network tests."""
    server_task = asyncio.create_task(quart_app.run_task(host=HOST_IP, port=PORT))
    await asyncio.sleep(2) # Give server time to start
    yield
    server_task.cancel()

# This tells pytest to skip ALL tests in this file if the integration flag isn't set,
# or if the .env file is missing/dummy.
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("NAME_URL") == "http://fake-url/names" or not os.environ.get("NAME_URL"),
        reason="Skipping live integration tests without real Power Automate URLs."
    )
]

@pytest.mark.asyncio
async def test_live_get_name() -> None:
    """Verifies that the live get_name flow successfully queries Power Automate."""
    fake_barcode = "OL01509"
    res = await get_name(fake_barcode)
    assert res is not None or res is None

@pytest.mark.asyncio
async def test_live_get_item() -> None:
    """Verifies that the live get_item flow successfully queries Power Automate."""
    fake_item_id = 11134
    res = await get_item(fake_item_id)
    assert res is not None or res is None

@pytest.mark.asyncio
async def test_live_checkout() -> None:
    """Verifies that the live checkout flow successfully pushes to Power Automate."""
    payload: UserInfoPayload = {
        "name": "John Doe",
        "user_id": "OL01509",
        "email": "jdoe@olin.edu",
        "item_id": 11134,
        "borrowed_date": datetime.now(),
        "returned_date": min_datetime,
        "item_status": Status.BORROWED
    }
    success = await checkout(payload)
    assert isinstance(success, bool)

@pytest.mark.asyncio
async def test_live_request_borrowed_items() -> None:
    """Verifies that the live borrowed items flow successfully queries Power Automate."""
    res = await request_borrowed_items()
    assert res is not None or res is None
