"""
Tests for safe API key rotation: current / old / pending keys in api_security, and the
recovery logic in requests.request_borrowed_items() and requests.resolve_pending_keys().

FakeKeyFlow mimics the real borrowed-items flow: Excel holds exactly one key; a rotation
request replaces it when x-old-key matches; a read-only request answers only when
x-api-key matches; the reply is signed with the key the flow accepted.
"""

from typing import Optional

import pytest
from dotenv import dotenv_values
from quart.testing import QuartClient
from pytest_mock import MockerFixture

import Email.email_service as es
from backend import api_security
from backend import requests as flow_requests
from backend.backend_constants import BORROWED_ITEMS_URL
from backend.requests import request_borrowed_items, resolve_pending_keys


class FakeResponse:
    """Stand-in for the httpx response from the flow trigger."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class FakeKeyFlow:
    """Behaves like the borrowed-items flow for key handling."""

    def __init__(self, client: QuartClient, excel_key: str) -> None:
        self.client = client
        self.excel_key = excel_key
        self.online = True  # False: trigger accepts the request but the flow never answers
        self.apply_rotation = True  # False: flow fails before saving the new key
        self.reply_to_rotation = True  # False: key saved, but the reply is lost
        self.trigger_status = 202
        self.rows = [
            {
                "Name": "Test User",
                "Email": "test@olin.edu",
                "ItemID": 11134,
                "DateBorrowed": 45000.0,
                "ItemStatus": "Borrowed",
            }
        ]

    async def post(
        self, url: str, json: dict, headers: Optional[dict] = None, timeout: float = 0
    ) -> FakeResponse:
        headers = headers or {}
        if url != BORROWED_ITEMS_URL:
            return FakeResponse(202)  # other flows (e.g. item names) never answer here
        if self.trigger_status not in (200, 202) or not self.online:
            return FakeResponse(self.trigger_status)

        request_id = json["RequestID"]
        if headers.get("x-is-rotation") == "true":
            if self.apply_rotation and headers.get("x-old-key") == self.excel_key:
                self.excel_key = headers["x-new-key"]
                if self.reply_to_rotation:
                    await self._reply(request_id, headers["x-new-key"])
        elif headers.get("x-api-key") == self.excel_key:
            await self._reply(request_id, self.excel_key)
        return FakeResponse(202)

    async def _reply(self, request_id: str, key: str) -> None:
        await self.client.post(
            "/borrowed-items",
            json={"RequestID": request_id, "excelData": self.rows},
            headers={"x-api-key": key},
        )


def set_keys(current: str, old: str, pending: tuple[str, ...] = ()) -> None:
    """Sets the kiosk's key state (conftest restores the real state afterwards)."""
    api_security._current_key = current
    api_security._old_key = old
    api_security._pending_keys = list(pending)


@pytest.fixture
def flow(client: QuartClient, mocker: MockerFixture, monkeypatch) -> FakeKeyFlow:
    """A fake flow holding key K1, with short callback waits so timeouts are quick."""
    monkeypatch.setattr(flow_requests, "CALLBACK_TIMEOUT", 0.3)
    fake = FakeKeyFlow(client, excel_key="K1")
    mocker.patch("backend.requests.post_json", side_effect=fake.post)
    return fake


# ---- api_security -----------------------------------------------------------


def test_revert_keeps_unconfirmed_key_as_pending() -> None:
    """Reverting never throws away the new key; it is parked as pending and saved."""
    set_keys(current="K2", old="K1")

    api_security.revert_api_keys()

    assert api_security.get_current_key() == "K1"
    assert api_security.get_pending_keys() == ["K2"]
    assert "K2" in api_security.accepted_keys()
    assert dotenv_values(api_security.ENV_FILE)["PENDING_API_KEYS"] == "K2"


def test_pending_keys_survive_a_restart(monkeypatch) -> None:
    """Pending keys written to .env are loaded again on the next start."""
    set_keys(current="K2", old="K1")
    api_security.revert_api_keys()

    set_keys(current=None, old=None)
    for var in ("CURRENT_API_KEY", "OLD_API_KEY", "PENDING_API_KEYS"):
        monkeypatch.delenv(var, raising=False)
    api_security.load_keys()

    assert api_security.get_current_key() == "K1"
    assert api_security.get_pending_keys() == ["K2"]


def test_revert_twice_is_harmless() -> None:
    """A second revert (current already equals old) changes nothing."""
    set_keys(current="K2", old="K1")
    api_security.revert_api_keys()
    api_security.revert_api_keys()

    assert api_security.get_current_key() == "K1"
    assert api_security.get_pending_keys() == ["K2"]


def test_confirm_pending_key_makes_it_current() -> None:
    """Confirming a pending key makes it current, keeps the previous key as old."""
    set_keys(current="K1", old="K0", pending=("K2", "K3"))

    api_security.confirm_pending_key("K2")

    assert api_security.get_current_key() == "K2"
    assert api_security.get_old_key() == "K1"
    assert api_security.get_pending_keys() == []


def test_abandon_rotation_drops_new_key() -> None:
    """Abandoning a rotation goes back to the old key without parking the new one."""
    set_keys(current="K2", old="K1")

    api_security.abandon_rotation()

    assert api_security.get_current_key() == "K1"
    assert api_security.get_pending_keys() == []


# ---- rotation through request_borrowed_items -----------------------------------


@pytest.mark.asyncio
async def test_rotation_confirmed_by_reply(flow: FakeKeyFlow) -> None:
    """Normal day: the flow saves the new key and replies; the new key stays current."""
    set_keys(current="K2", old="K1")

    rows = await request_borrowed_items()

    assert rows is not None and len(rows) == 1
    assert flow.excel_key == "K2"
    assert api_security.get_current_key() == "K2"
    assert api_security.get_pending_keys() == []


@pytest.mark.asyncio
async def test_lost_reply_but_new_key_saved(flow: FakeKeyFlow) -> None:
    """The old lockout case: reply lost after Excel saved the new key. Kiosk keeps it."""
    set_keys(current="K2", old="K1")
    flow.reply_to_rotation = False

    rows = await request_borrowed_items()

    assert rows is not None
    assert flow.excel_key == "K2"
    assert api_security.get_current_key() == "K2"
    assert api_security.get_pending_keys() == []


@pytest.mark.asyncio
async def test_rotation_not_saved_goes_back_to_old_key(flow: FakeKeyFlow) -> None:
    """The flow never saved the new key: the kiosk returns to the key Excel holds."""
    set_keys(current="K2", old="K1")
    flow.apply_rotation = False

    rows = await request_borrowed_items()

    assert rows is None
    assert flow.excel_key == "K1"
    assert api_security.get_current_key() == "K1"
    assert api_security.get_pending_keys() == []


@pytest.mark.asyncio
async def test_trigger_rejects_rotation_goes_back_to_old_key(flow: FakeKeyFlow) -> None:
    """Power Automate answered 500, so the flow never ran: undo the rotation at once."""
    set_keys(current="K2", old="K1")
    flow.trigger_status = 500

    assert await request_borrowed_items() is None
    assert api_security.get_current_key() == "K1"
    assert api_security.get_pending_keys() == []


@pytest.mark.asyncio
async def test_flow_unreachable_keeps_both_keys_until_resolved(flow: FakeKeyFlow) -> None:
    """Nothing answers: the new key is parked as pending and confirmed later."""
    set_keys(current="K2", old="K1")
    flow.online = False
    flow.excel_key = "K2"  # the flow did save the new key; we just can't tell yet

    assert await request_borrowed_items() is None
    api_security.revert_api_keys()  # what the reminder job does on None
    assert api_security.get_current_key() == "K1"
    assert api_security.get_pending_keys() == ["K2"]

    flow.online = True
    await resolve_pending_keys()

    assert api_security.get_current_key() == "K2"
    assert api_security.get_old_key() == "K1"
    assert api_security.get_pending_keys() == []


@pytest.mark.asyncio
async def test_resolve_discards_pending_when_current_key_is_live(flow: FakeKeyFlow) -> None:
    """Excel still holds the current key: pending keys are dropped."""
    set_keys(current="K1", old="K0", pending=("K2",))

    await resolve_pending_keys()

    assert api_security.get_current_key() == "K1"
    assert api_security.get_pending_keys() == []


@pytest.mark.asyncio
async def test_resolve_keeps_pending_while_flow_is_down(flow: FakeKeyFlow) -> None:
    """While nothing answers, pending keys are kept for the next check."""
    set_keys(current="K1", old="K0", pending=("K2",))
    flow.online = False

    await resolve_pending_keys()

    assert api_security.get_current_key() == "K1"
    assert api_security.get_pending_keys() == ["K2"]


@pytest.mark.asyncio
async def test_resolve_without_pending_keys_sends_nothing(flow: FakeKeyFlow, mocker) -> None:
    """With no pending keys, the background check makes no requests."""
    spy = mocker.patch("backend.requests.post_json")
    set_keys(current="K1", old="K0")

    await resolve_pending_keys()

    spy.assert_not_called()


# ---- the unchanged reminder job, end to end ------------------------------------------


@pytest.mark.asyncio
async def test_reminder_job_survives_lost_rotation_reply(
    flow: FakeKeyFlow, mocker: MockerFixture
) -> None:
    """email_service (unchanged) rotates; the reply is lost; the kiosk keeps working."""
    mocker.patch.object(es, "_send_batch_reminder_emails")
    set_keys(current="K1", old="K0")
    flow.reply_to_rotation = False

    await es.send_overdue_reminders()

    new_key = api_security.get_current_key()
    assert new_key != "K1"
    assert flow.excel_key == new_key
    assert api_security.get_pending_keys() == []


@pytest.mark.asyncio
async def test_reminder_job_with_flow_down_never_loses_a_key(
    flow: FakeKeyFlow, mocker: MockerFixture
) -> None:
    """email_service (unchanged) rotates while the flow is down: no key is lost."""
    mocker.patch.object(es, "_send_batch_reminder_emails")
    set_keys(current="K1", old="K0")
    flow.online = False

    await es.send_overdue_reminders()

    assert api_security.get_current_key() == "K1"
    assert len(api_security.get_pending_keys()) == 1
    assert flow.excel_key in api_security.accepted_keys()
