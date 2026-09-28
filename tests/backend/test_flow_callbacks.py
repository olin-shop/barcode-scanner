"""
Tests for callback handling added to endpoints.py: flow-reported errors fail the waiting
request immediately, pending API keys are accepted, and malformed bodies don't crash.
"""

import asyncio
import time

import pytest
from quart.testing import QuartClient
from pytest_mock import MockerFixture

from backend import api_security
from backend import requests as flow_requests
from backend.app_state import pending_requests
from backend.backend_types import FlowError, Status, UserInfoPayload
from backend.backend_constants import min_datetime
from backend.requests import checkout, get_item


class FakeResponse:
    """Stand-in for the httpx response from the flow trigger."""

    def __init__(self, status_code: int = 202) -> None:
        self.status_code = status_code


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "route", ["/checkout", "/items", "/names", "/borrowed-items", "/intro-sheet", "/303-sheet"]
)
async def test_error_callback_fails_waiting_request(client: QuartClient, route: str) -> None:
    """An {"Error": ...} callback on any route fails the matching future with FlowError."""
    request_id = f"err-{route}"
    future = asyncio.get_running_loop().create_future()
    pending_requests[request_id] = future

    response = await client.post(
        route,
        json={"RequestID": request_id, "Error": "NotFound"},
        headers={"x-api-key": api_security.get_current_key()},
    )
    await asyncio.sleep(0)

    assert response.status_code == 200
    assert isinstance(future.exception(), FlowError)
    assert request_id not in pending_requests


@pytest.mark.asyncio
async def test_error_callback_returns_fast(
    client: QuartClient, mocker: MockerFixture, monkeypatch
) -> None:
    """get_item gives up as soon as the flow reports an error, instead of waiting."""
    monkeypatch.setattr(flow_requests, "CALLBACK_TIMEOUT", 10.0)

    async def flow_reports_not_found(url, json, headers=None, timeout=0):
        await client.post(
            "/items",
            json={"RequestID": json["RequestID"], "Error": "NotFound"},
            headers={"x-api-key": api_security.get_current_key()},
        )
        return FakeResponse(202)

    mocker.patch("backend.requests.post_json", side_effect=flow_reports_not_found)

    started = time.monotonic()
    assert await get_item(99999) is None
    assert time.monotonic() - started < 2.0


@pytest.mark.asyncio
async def test_checkout_error_callback_returns_false(
    client: QuartClient, mocker: MockerFixture
) -> None:
    """A checkout the flow rejects comes back False right away."""

    async def flow_rejects(url, json, headers=None, timeout=0):
        await client.post(
            "/checkout",
            json={"RequestID": json["RequestID"], "Error": "ItemBorrowedByAnotherUser"},
            headers={"x-api-key": api_security.get_current_key()},
        )
        return FakeResponse(202)

    mocker.patch("backend.requests.post_json", side_effect=flow_rejects)
    payload: UserInfoPayload = {
        "name": "Test User",
        "email": "test@olin.edu",
        "item_id": 11134,
        "borrowed_date": min_datetime,
        "returned_date": min_datetime,
        "item_status": Status.BORROWED,
    }

    assert await checkout(payload) is False


@pytest.mark.asyncio
async def test_pending_key_is_accepted(client: QuartClient) -> None:
    """A callback signed with a pending (unconfirmed) key is accepted."""
    api_security._pending_keys = ["pending-key-123"]

    response = await client.post(
        "/checkout",
        json={"RequestID": "nobody-waiting", "Sent": "Received"},
        headers={"x-api-key": "pending-key-123"},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_unknown_key_is_rejected(client: QuartClient) -> None:
    """A callback signed with any other key is refused."""
    response = await client.post(
        "/checkout",
        json={"RequestID": "nobody-waiting", "Sent": "Received"},
        headers={"x-api-key": "not-a-kiosk-key"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_malformed_body_does_not_crash(client: QuartClient) -> None:
    """A callback whose body isn't JSON is logged and answered, not a 500."""
    response = await client.post(
        "/items",
        data="this is not json",
        headers={"x-api-key": api_security.get_current_key(), "Content-Type": "text/plain"},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_checkout_waits_longer_than_other_calls(
    client: QuartClient, mocker: MockerFixture, monkeypatch
) -> None:
    """Checkout uses its own, longer wait (Excel writes can take up to 30 seconds)."""
    monkeypatch.setattr(flow_requests, "CALLBACK_TIMEOUT", 0.05)
    monkeypatch.setattr(flow_requests, "CHECKOUT_CALLBACK_TIMEOUT", 2.0)

    async def slow_flow(url, json, headers=None, timeout=0):
        async def reply_later():
            await asyncio.sleep(0.3)  # slower than CALLBACK_TIMEOUT, within checkout's wait
            await client.post(
                "/checkout",
                json={"RequestID": json["RequestID"], "Sent": "Received"},
                headers={"x-api-key": api_security.get_current_key()},
            )

        asyncio.get_running_loop().create_task(reply_later())
        return FakeResponse(202)

    mocker.patch("backend.requests.post_json", side_effect=slow_flow)
    payload: UserInfoPayload = {
        "name": "Test User",
        "email": "test@olin.edu",
        "item_id": 11134,
        "borrowed_date": min_datetime,
        "returned_date": min_datetime,
        "item_status": Status.BORROWED,
    }

    assert await checkout(payload) is True


@pytest.mark.asyncio
async def test_fetched_sheet_is_saved_to_disk_immediately(
    client: QuartClient, mocker: MockerFixture, monkeypatch
) -> None:
    """A fetched roster sheet is written to the cache folder right away, not only on close."""
    from backend import app_state

    monkeypatch.setitem(app_state.sheet_cache, "intro", {"data": None, "timestamp": None})
    rows = [{"Trainee Name": "Test User", "Trainee Email": "test@olin.edu", "Training Complete": True}]

    async def intro_flow(url, json, headers=None, timeout=0):
        await client.post(
            "/intro-sheet",
            json={"RequestID": json["RequestID"], "excelData": rows},
            headers={"x-api-key": api_security.get_current_key()},
        )
        return FakeResponse(202)

    mocker.patch("backend.requests.post_json", side_effect=intro_flow)

    df = await flow_requests.gather_intro_data()

    assert df is not None and len(df) == 1
    assert (app_state.CACHE_DIR / "intro_sheet.csv").exists()
    assert app_state.sheet_cache["intro"]["data"] is df


@pytest.mark.asyncio
async def test_empty_sheet_is_not_cached(
    client: QuartClient, mocker: MockerFixture, monkeypatch
) -> None:
    """An empty reply isn't cached, so a glitch can't hide every name for a day."""
    from backend import app_state

    monkeypatch.setitem(app_state.sheet_cache, "303", {"data": None, "timestamp": None})

    async def empty_flow(url, json, headers=None, timeout=0):
        await client.post(
            "/303-sheet",
            json={"RequestID": json["RequestID"], "excelData": []},
            headers={"x-api-key": api_security.get_current_key()},
        )
        return FakeResponse(202)

    mocker.patch("backend.requests.post_json", side_effect=empty_flow)

    await flow_requests.gather_303_data()

    assert app_state.sheet_cache["303"]["data"] is None
    assert not (app_state.CACHE_DIR / "303_sheet.csv").exists()
