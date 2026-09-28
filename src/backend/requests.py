"""
This includes functions for sending requests to our database pipeline.
The functions wait for incoming data which is received and matched up at our endpoints.
"""

import asyncio
import logging
import uuid
import weakref
from datetime import datetime
from typing import Any, Optional

import pandas as pd

from backend import api_security
from backend.api_security import get_current_key, get_old_key
from backend.app_state import (
    item_cache,
    pending_requests,
    save_sheet_cache_to_disk,
    sheet_cache,
)
from backend.backend_constants import (
    BORROWED_ITEMS_URL,
    CHECKOUT_URL,
    DAY_IN_SECONDS,
    ELEC_URL,
    INTRO_URL,
    ITEM_URL,
    NAME_URL,
    TIMEOUT,
    db_to_class_conversion,
    to_excel_date,
)
from backend.backend_types import FlowError, Status, UserInfoPayload
from backend.http_client import HTTP_ERRORS, MAYBE_DELIVERED_ERRORS, post_json

logger = logging.getLogger(__name__)

# Seconds to wait for Power Automate to call back.
CALLBACK_TIMEOUT: float = 15.0

# Checkout writes to Excel, which Microsoft says can take up to 30 seconds. Waiting
# longer keeps a slow success from being reported as a failure and retried into a
# duplicate row.
CHECKOUT_CALLBACK_TIMEOUT: float = 30.0

# How often the background task re-checks unconfirmed (pending) API keys.
PENDING_KEY_CHECK_INTERVAL: float = 600.0

# Serializes everything that changes which API key is current (rotation recovery and
# pending-key checks) so two of them can never interleave. One lock per event loop,
# because an asyncio.Lock must not be shared between loops; in the app, all key work
# runs on the Quart/scheduler loop.
_key_locks: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Lock]" = (
    weakref.WeakKeyDictionary()
)


def _key_lock() -> asyncio.Lock:
    """Returns the key lock for the running event loop."""
    loop = asyncio.get_running_loop()
    lock = _key_locks.get(loop)
    if lock is None:
        lock = _key_locks[loop] = asyncio.Lock()
    return lock

BorrowedRecord = tuple[str, str, str, int, datetime, Status]


class FlowDispatchError(Exception):
    """
    The request never got a successful reply from Power Automate's trigger.
    `maybe_delivered` is True when the connection broke after sending, so the flow
    might have run anyway.
    """

    def __init__(self, message: str, maybe_delivered: bool = False) -> None:
        super().__init__(message)
        self.maybe_delivered = maybe_delivered


async def _call_flow(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    description: str,
    wait_seconds: Optional[float] = None,
) -> Any:
    """
    Sends `payload` to a flow and waits for the callback carrying the same RequestID.

    Registers an asyncio Future under payload["RequestID"], POSTs the payload, then waits
    up to `wait_seconds` (default CALLBACK_TIMEOUT) for the matching endpoint in
    endpoints.py to fulfill it. The pending entry is always removed, whatever happens.

    Raises
    ------
    FlowDispatchError
        The POST failed or Power Automate answered with a non-2xx status.
    asyncio.TimeoutError
        No callback arrived in time.
    FlowError
        The flow called back with an "Error" field.
    ValueError
        The callback carried data that couldn't be parsed.
    """
    request_id: str = payload["RequestID"]
    future: asyncio.Future = asyncio.get_running_loop().create_future()
    pending_requests[request_id] = future

    logger.info("Initiating %s (RequestID=%s).", description, request_id)
    try:
        try:
            res = await post_json(url, json=payload, headers=headers, timeout=TIMEOUT)
        except HTTP_ERRORS as e:
            raise FlowDispatchError(
                f"{type(e).__name__}: {e}",
                maybe_delivered=isinstance(e, MAYBE_DELIVERED_ERRORS),
            ) from e
        if res.status_code not in (200, 202):
            raise FlowDispatchError(f"HTTP dispatch status {res.status_code}")

        wait = CALLBACK_TIMEOUT if wait_seconds is None else wait_seconds
        result = await asyncio.wait_for(future, timeout=wait)
        logger.info("Received %s result (RequestID=%s).", description, request_id)
        return result
    finally:
        pending_requests.pop(request_id, None)


def _log_failure(description: str, error: BaseException) -> None:
    """Logs why a flow call failed, in words that say where the problem is."""
    if isinstance(error, FlowDispatchError):
        logger.error("Failed to send %s: %s", description, error)
    elif isinstance(error, asyncio.TimeoutError):
        logger.warning("Timeout: Power Automate never responded for %s.", description)
    elif isinstance(error, FlowError):
        logger.warning("Power Automate reported an error for %s: %s", description, error)
    else:
        logger.error("Data error in %s: %s", description, error)


# Everything _call_flow can raise for a failed call. TypeError/KeyError/AttributeError
# come from the sheet endpoints when a callback's rows can't become a DataFrame.
_FLOW_FAILURES = (
    FlowDispatchError,
    asyncio.TimeoutError,
    FlowError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
)


async def get_name(
    email: str,
) -> Optional[tuple[str, str, list[datetime], list[Status], list[int]]]:
    """
    Gathers the name and currently borrowed items attached to a given email.

    Sends the email and a unique RequestID to the name flow, then waits (up to 15
    seconds) for the `/names` endpoint to receive the matching callback.

    Parameters
    ----------
    email : str
        The email attached to the name.

    Returns
    -------
    Optional[tuple[str, str, list[datetime], list[Status], list[int]]]
        A tuple of the user's name, their email, the times they borrowed items,
        the statuses of those items, and the item IDs. Returns None if the
        request fails, times out, or the flow reports an error.
    """
    description = f"get_name for user_email={email}"
    payload = {"Email": email, "RequestID": str(uuid.uuid4())}
    try:
        return await _call_flow(
            NAME_URL, payload, {"x-api-key": get_current_key()}, description
        )
    except _FLOW_FAILURES as e:
        _log_failure(description, e)
        return None


async def get_item(barcode: int) -> Optional[tuple[str, Status]]:
    """
    Gathers the item name and status attached to a given barcode.

    Sends the barcode and a unique RequestID to the item flow, then waits (up to 15
    seconds) for the `/items` endpoint to receive the matching callback. Successful
    lookups are remembered in the item-name cache.

    Parameters
    ----------
    barcode : int
        The barcode attached to the item.

    Returns
    -------
    Optional[tuple[str, Status]]
        A tuple containing the name of the item and its current status.
        Returns None if the request fails, times out, or the flow reports an error.
    """
    description = f"get_item for item_id={barcode}"
    payload = {"ItemID": barcode, "RequestID": str(uuid.uuid4())}
    try:
        result = await _call_flow(
            ITEM_URL, payload, {"x-api-key": get_current_key()}, description
        )
    except _FLOW_FAILURES as e:
        _log_failure(description, e)
        return None

    if result:
        item_name, _status = result
        if item_name:
            item_cache[barcode] = item_name
    return result


async def get_item_name_cached(barcode: int) -> str:
    """
    Returns the item name for a given barcode, checking the local cache first.
    If it's not cached, it awaits get_item(barcode) to query the backend and populate the cache.
    """
    if barcode in item_cache:
        return item_cache[barcode]

    res = await get_item(barcode)
    if res:
        item_name, _ = res
        if item_name:
            return item_name
    return f"Item ({barcode})"


async def checkout(user_info: UserInfoPayload) -> bool:
    """
    Commits a user checkout or return to the database pipeline.

    Converts datetimes to Excel serial numbers, sends the row to the checkout flow,
    and waits (up to 30 seconds, since Excel writes can be slow) for the `/checkout`
    endpoint to receive the confirmation.

    Parameters
    ----------
    user_info : UserInfoPayload
        Info of the user for their checkout.
        Structure:
        {
            "Name": str - Their name.
            "Email": str - Their email.
            "ItemID": int - A set of 5 numbers.
            "DateBorrowed": datetime - The date and time the user borrowed the item.
            "DateReturned": datetime - The date and time the user returned the item.
            "ItemStatus": Status (StrEnum) (Borrowed, In Stock, Missing)
        }

    Returns
    -------
    bool
        True if the checkout was confirmed, False if it failed, timed out, or the
        flow reported an error.
    """
    request_id: str = str(uuid.uuid4())
    send_json: dict[str, str | int | float] = {
        "Name": "",
        "Email": "",
        "ItemID": 0,
        "DateBorrowed": 0.0,
        "DateReturned": 0.0,
        "ItemStatus": "",
        "RequestID": request_id,
    }

    for key in send_json:
        if key == "RequestID":
            continue
        user_info_key: str = db_to_class_conversion[key]
        match user_info[user_info_key]:
            case datetime():
                send_json[key] = to_excel_date(user_info[user_info_key])
            case str() | int():
                send_json[key] = user_info[user_info_key]
            case Status():
                send_json[key] = user_info[user_info_key].value

    description = (
        f"checkout for user={user_info.get('email')} item={user_info.get('item_id')} "
        f"status={user_info.get('item_status')}"
    )
    try:
        result = await _call_flow(
            CHECKOUT_URL,
            send_json,
            {"x-api-key": get_current_key()},
            description,
            wait_seconds=CHECKOUT_CALLBACK_TIMEOUT,
        )
    except _FLOW_FAILURES as e:
        _log_failure(description, e)
        return False
    return bool(result)


async def fetch_borrowed_items_with_key(api_key: str) -> Optional[list[BorrowedRecord]]:
    """
    Asks the borrowed-items flow for the full list without rotating keys, signing the
    request with `api_key`. Doubles as a probe: a reply means Power Automate currently
    accepts that key.

    Returns
    -------
    Optional[list[BorrowedRecord]]
        The borrowed-item records, or None if the flow didn't answer.
    """
    description = "borrowed-items check"
    headers = {"x-api-key": api_key, "x-is-rotation": "false"}
    try:
        return await _call_flow(
            BORROWED_ITEMS_URL, {"RequestID": str(uuid.uuid4())}, headers, description
        )
    except _FLOW_FAILURES as e:
        _log_failure(description, e)
        return None


async def request_borrowed_items() -> Optional[list[BorrowedRecord]]:
    """
    Requests a list of all currently borrowed items, and saves the rotated API key in
    Power Automate at the same time.

    The reminder job calls api_security.rotate_api_keys() first, so the current key is
    the new, unconfirmed one and the old key is the one Power Automate holds. This sends
    both; the flow stores the new key and replies with the list.

    If the reply never arrives, the flow may or may not have saved the new key. Instead
    of guessing, this checks with Power Automate (new key first, then old) and keeps
    whichever one it accepts:
    - new key accepted: the rotation worked; returns the list.
    - old key accepted: the rotation didn't happen; undoes it and returns None.
    - neither answered: returns None; the caller's revert_api_keys() keeps the new key
      as pending until keep_resolving_pending_keys() settles it.

    Returns
    -------
    Optional[list[BorrowedRecord]]
        A list of tuples (user_id, name, email, item_id, time_borrowed, status),
        or None if the rotation couldn't be confirmed.
    """
    new_key, old_key = get_current_key(), get_old_key()
    description = "request_borrowed_items (key rotation)"
    headers = {
        "x-api-key": old_key,
        "x-new-key": new_key,
        "x-old-key": old_key,
        "x-is-rotation": "true",
    }

    async with _key_lock():
        try:
            return await _call_flow(
                BORROWED_ITEMS_URL,
                {"RequestID": str(uuid.uuid4())},
                headers,
                description,
            )
        except FlowDispatchError as e:
            _log_failure(description, e)
            if not e.maybe_delivered:
                # Power Automate never ran the flow, so it still holds the old key.
                api_security.abandon_rotation()
                return None
        except _FLOW_FAILURES as e:
            _log_failure(description, e)

        logger.warning(
            "Rotation reply missing; checking which API key Power Automate holds."
        )
        if new_key != old_key:
            rows = await fetch_borrowed_items_with_key(new_key)
            if rows is not None:
                logger.info("Power Automate accepted the new API key; rotation kept.")
                return rows

        if await fetch_borrowed_items_with_key(old_key) is not None:
            api_security.abandon_rotation()
            return None

        logger.error(
            "Couldn't confirm which API key Power Automate holds; both are kept "
            "and will be re-checked every %d minutes.",
            int(PENDING_KEY_CHECK_INTERVAL // 60),
        )
        return None


async def resolve_pending_keys() -> None:
    """
    Settles keys left pending by an unconfirmed rotation: whichever key Power Automate
    accepts becomes current. Does nothing when there are no pending keys.
    """
    async with _key_lock():
        pending = api_security.get_pending_keys()
        if not pending:
            return

        logger.info("Checking %d pending API key(s) with Power Automate.", len(pending))
        for key in pending:
            if await fetch_borrowed_items_with_key(key) is not None:
                api_security.confirm_pending_key(key)
                return

        if await fetch_borrowed_items_with_key(get_current_key()) is not None:
            api_security.discard_pending_keys()
            return

        logger.error(
            "Power Automate accepted none of the kiosk's API keys; will retry in %d minutes.",
            int(PENDING_KEY_CHECK_INTERVAL // 60),
        )


async def keep_resolving_pending_keys(
    interval_seconds: float = PENDING_KEY_CHECK_INTERVAL,
) -> None:
    """Background loop: checks pending API keys at startup and then every interval."""
    while True:
        try:
            await resolve_pending_keys()
        except Exception:  # keep the loop alive whatever goes wrong
            logger.exception("Pending API key check failed.")
        await asyncio.sleep(interval_seconds)


async def _gather_sheet(key: str, url: str) -> Optional[pd.DataFrame]:
    """
    Returns the "intro" or "303" sheet as a DataFrame, using the 24-hour cache when
    it's fresh, otherwise fetching it from Power Automate and saving it to disk.
    """
    cache = sheet_cache[key]
    if cache["data"] is not None and cache["timestamp"] is not None:
        if (datetime.now() - cache["timestamp"]).total_seconds() < DAY_IN_SECONDS:
            logger.info("Using cached %s-sheet data.", key)
            return cache["data"]

    description = f"gather_{key}_data"
    try:
        result = await _call_flow(
            url,
            {"RequestID": str(uuid.uuid4())},
            {"x-api-key": get_current_key()},
            description,
        )
    except _FLOW_FAILURES as e:
        _log_failure(description, e)
        return None

    # Only cache a sheet that has rows; caching an empty reply would hide everyone's
    # name for a full day.
    if isinstance(result, pd.DataFrame) and not result.empty:
        cache["data"] = result
        cache["timestamp"] = datetime.now()
        await asyncio.to_thread(save_sheet_cache_to_disk, key)
    else:
        logger.warning("%s-sheet reply had no rows; not caching it.", key)
    return result


async def gather_intro_data() -> Optional[pd.DataFrame]:
    """
    Requests the intro sheet data from Power Automate.
    Checks the 24-hour cache first before making the request.

    Returns
    -------
    Optional[pd.DataFrame]
        A pandas DataFrame containing the sheet data. Returns None if the
        request fails or times out.
    """
    return await _gather_sheet("intro", INTRO_URL)


async def gather_303_data() -> Optional[pd.DataFrame]:
    """
    Requests the 303 sheet data from Power Automate.
    Checks the 24-hour cache first before making the request.

    Returns
    -------
    Optional[pd.DataFrame]
        A pandas DataFrame containing the sheet data. Returns None if the
        request fails or times out.
    """
    return await _gather_sheet("303", ELEC_URL)
