"""
Unit tests for the Quart webhooks in endpoints.py.
Verifies that incoming webhook payloads from Power Automate are parsed safely
and that the asynchronous pending_requests futures are resolved correctly.
"""

from datetime import datetime
import asyncio

from quart.testing import QuartClient
import pytest

from backend.backend_types import Status
from backend.app_state import pending_requests
from backend.api_security import get_current_key


@pytest.mark.asyncio
async def test_checkout_endpoint(client: QuartClient) -> None:
    """Verifies that the /checkout endpoint successfully resolves the pending future with True."""
    request_id = "test-req-1"
    future = asyncio.get_running_loop().create_future()
    pending_requests[request_id] = future

    headers = {"x-api-key": get_current_key()}
    response = await client.post(
        "/checkout", json={"RequestID": request_id, "Sent": "Received"}, headers=headers
    )
    assert response.status_code == 200

    assert future.result() is True


@pytest.mark.asyncio
async def test_get_item_endpoint(client: QuartClient) -> None:
    """Verifies that the /items endpoint correctly parses item data and resolves the future."""
    request_id = "test-req-2"
    future = asyncio.get_running_loop().create_future()
    pending_requests[request_id] = future
    headers = {"x-api-key": get_current_key()}
    response = await client.post(
        "/items",
        json={"RequestID": request_id, "ItemName": "Drill", "ItemStatus": "In Stock"},
        headers=headers,
    )
    assert response.status_code == 200

    result = future.result()
    assert result == ("Drill", Status.INSTOCK)


@pytest.mark.asyncio
async def test_get_name_endpoint(client: QuartClient) -> None:
    """Verifies that the /names endpoint parses user and item history data correctly."""
    request_id = "test-req-3"
    future = asyncio.get_running_loop().create_future()
    pending_requests[request_id] = future
    # 44000.0 is roughly June 2020 in Excel dates
    headers = {"x-api-key": get_current_key()}
    response = await client.post(
        "/names",
        json={
            "RequestID": request_id,
            "Name": "Alice",
            "Email": "alice@example.com",
            "excelData": [
                {"ItemID": "123", "ItemStatus": "Borrowed", "DateBorrowed": 44000.0}
            ],
        },
        headers=headers,
    )
    assert response.status_code == 200

    name, email, dates, statuses, item_ids = future.result()
    assert name == "Alice"
    assert email == "alice@example.com"
    assert item_ids == [123]
    assert statuses == [Status.BORROWED]
    assert len(dates) == 1


@pytest.mark.asyncio
async def test_borrowed_items_endpoint(client: QuartClient) -> None:
    """Verifies that the /borrowed-items endpoint parses dates and statuses correctly."""
    request_id = "test-req-4"
    future = asyncio.get_running_loop().create_future()
    pending_requests[request_id] = future
    headers = {"x-api-key": get_current_key()}
    response = await client.post(
        "/borrowed-items",
        json={
            "RequestID": request_id,
            "excelData": [
                {
                    "ItemID": "456",
                    "ItemStatus": "Missing",
                    "DateBorrowed": 45000.0,
                    "Name": "Alice",
                    "Email": "alice@example.com",
                }
            ],
        },
        headers=headers,
    )
    assert response.status_code == 200

    results = future.result()
    assert len(results) == 1
    user_id, name, email, item_id, borrowed_at, status = results[0]
    
    assert name == "Alice"
    assert email == "alice@example.com"
    assert item_id == 456
    assert status == Status.MISSING
    assert isinstance(borrowed_at, datetime)


@pytest.mark.asyncio
async def test_malformed_json_missing_request_id(client: QuartClient) -> None:
    """Ensure the endpoint doesn't crash if RequestID is missing."""
    headers = {"x-api-key": get_current_key()}
    response = await client.post(
        "/items", json={"ItemName": "Drill", "ItemStatus": "In Stock"}, headers=headers
    )
    assert response.status_code == 200
    # Since there's no RequestID, it shouldn't pop anything from pending_requests
    assert len(pending_requests) == 0


@pytest.mark.asyncio
async def test_malformed_date_borrowed_items(client: QuartClient) -> None:
    """Ensure the endpoint gracefully flags items with un-parseable dates."""
    request_id = "test-req-bad-date"
    future = asyncio.get_running_loop().create_future()
    pending_requests[request_id] = future
    headers = {"x-api-key": get_current_key()}
    response = await client.post(
        "/borrowed-items",
        json={
            "RequestID": request_id,
            "excelData": [
                {
                    "ItemID": "100",
                    "ItemStatus": "Borrowed",
                    "DateBorrowed": "GARBAGE_STRING",
                    "Name": "Bad Date User",
                    "Email": "bad@example.com",
                },
                {
                    "ItemID": "101",
                    "ItemStatus": "Borrowed",
                    "DateBorrowed": 45000.0,
                    "Name": "Good Date User",
                    "Email": "good@example.com",
                },
            ],
        },
        headers=headers,
    )
    assert response.status_code == 200

    try:
        exc = future.exception()
        assert "Corrupted row data" in str(exc)
    except asyncio.InvalidStateError:
        pytest.fail("Future was not fulfilled with exception.")


@pytest.mark.asyncio
async def test_unauthorized_access(client: QuartClient) -> None:
    """Verifies that missing or invalid x-api-key headers result in a 401 Unauthorized."""
    # Missing header
    response = await client.post(
        "/checkout", json={"RequestID": "test", "Sent": "Received"}
    )
    assert response.status_code == 401

    # Invalid header
    response = await client.post(
        "/checkout",
        json={"RequestID": "test", "Sent": "Received"},
        headers={"x-api-key": "HACKER"},
    )
    assert response.status_code == 401
