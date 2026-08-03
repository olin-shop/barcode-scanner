"""
This includes functions for sending requests to our database pipeline.
The functions wait for incoming data which is received and matched up at our endpoints.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

import pandas as pd
import requests_async as requests

from backend.api_security import get_current_key, get_old_key
from backend.app_state import pending_requests, sheet_cache
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
from backend.backend_types import Status, UserInfoPayload

logger = logging.getLogger(__name__)


async def get_name(
    email: str,
) -> Optional[tuple[str, str, list[datetime], list[Status], list[int]]]:
    """
    Gathers the name and currently borrowed items attached to a given email.

    This function generates a unique request identifier and creates an asynchronous
    placeholder. It sends a POST request to the Power Automate pipeline, passing along
    both the email and the unique ID. It then pauses execution (for up to 15 seconds)
    until the `/names` endpoint receives the matching webhook callback and fulfills
    the placeholder with the requested data.

    Parameters
    ----------
    email : str
        The email attached to the name.

    Returns
    -------
    Optional[tuple[str, str, list[datetime], list[Status], list[int]]]
        A tuple of the user's name, their email, the times they borrowed items,
        the statuses of those items, and the item IDs. Returns None if the
        request fails or times out.
    """
    request_id: str = str(uuid.uuid4())
    send_json: dict[str, str] = {"Email": email, "RequestID": request_id}

    future: asyncio.Future = asyncio.get_running_loop().create_future()
    pending_requests[request_id] = future

    logger.info(
        "Initiating get_name request for user_email=%s (RequestID=%s).",
        email,
        request_id,
    )

    try:
        headers = {"x-api-key": get_current_key()}
        res = await requests.post(
            NAME_URL, json=send_json, headers=headers, timeout=TIMEOUT
        )
        if res.status_code not in (200, 202):
            raise ValueError(f"HTTP dispatch status {res.status_code}")
    except Exception as e:
        pending_requests.pop(request_id, None)
        logger.error("Failed to send get_name request for user_email=%s: %s", email, e)
        return None

    try:
        result = await asyncio.wait_for(future, timeout=15.0)
        logger.info(
            "Successfully received get_name result for user_email=%s (RequestID=%s).",
            email,
            request_id,
        )
        return result
    except asyncio.TimeoutError:
        pending_requests.pop(request_id, None)
        logger.warning(
            "Timeout: Power Automate never responded for get_name RequestID=%s (user_email=%s).",
            request_id,
            email,
        )
        return None
    except ValueError as e:
        logger.error("Data error in get_name for RequestID=%s: %s", request_id, e)
        return None


async def get_item(barcode: int) -> Optional[tuple[str, Status]]:
    """
    Gathers the item name and status attached to a given barcode.

    This function generates a unique request identifier and creates an asynchronous
    placeholder. It sends a POST request to the item database pipeline with the barcode
    and the unique ID. It then pauses execution (for up to 15 seconds) until the
    `/items` endpoint receives the callback and fulfills the placeholder with the data.

    Parameters
    ----------
    barcode : int
        The barcode attached to the item.

    Returns
    -------
    Optional[tuple[str, Status]]
        A tuple containing the name of the item and its current status.
        Returns None if the request fails or times out.
    """
    request_id: str = str(uuid.uuid4())
    send_json: dict[str, str | int] = {"ItemID": barcode, "RequestID": request_id}

    future: asyncio.Future = asyncio.get_running_loop().create_future()
    pending_requests[request_id] = future

    logger.info(
        "Initiating get_item request for item_id=%d (RequestID=%s).",
        barcode,
        request_id,
    )

    try:
        headers = {"x-api-key": get_current_key()}
        res = await requests.post(
            ITEM_URL, json=send_json, headers=headers, timeout=TIMEOUT
        )
        if res.status_code not in (200, 202):
            raise ValueError(f"HTTP dispatch status {res.status_code}")
    except Exception as e:
        pending_requests.pop(request_id, None)
        logger.error("Failed to send get_item request for item_id=%d: %s", barcode, e)
        return None

    try:
        result = await asyncio.wait_for(future, timeout=15.0)
        logger.info(
            "Successfully received get_item result for item_id=%d (RequestID=%s).",
            barcode,
            request_id,
        )
        return result
    except asyncio.TimeoutError:
        pending_requests.pop(request_id, None)
        logger.warning(
            "Timeout: Power Automate never responded for get_item RequestID=%s (item_id=%d).",
            request_id,
            barcode,
        )
        return None
    except ValueError as e:
        logger.error("Data error in get_item for RequestID=%s: %s", request_id, e)
        return None


async def checkout(user_info: UserInfoPayload) -> bool:
    """
    Commits a user checkout or return to the database pipeline.

    This function structures the provided user info dictionary, converts datetime
    objects into Excel-compatible floats, and injects a unique request identifier.
    It sends a POST request to the checkout pipeline and creates an asynchronous
    placeholder, pausing execution (for up to 15 seconds) until the `/checkout`
    endpoint receives the webhook confirmation and fulfills the placeholder.

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
        Returns True if the checkout has been received successfully, or False if
        it fails or times out.
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

    future: asyncio.Future = asyncio.get_running_loop().create_future()
    pending_requests[request_id] = future

    logger.info(
        "Initiating checkout pipeline commit for user=%s item=%s (Status=%s, RequestID=%s).",
        user_info.get("email"),
        user_info.get("item_id"),
        user_info.get("item_status"),
        request_id,
    )

    try:
        headers = {"x-api-key": get_current_key()}
        res = await requests.post(
            CHECKOUT_URL, json=send_json, headers=headers, timeout=TIMEOUT
        )
        if res.status_code not in (200, 202):
            raise ValueError(f"HTTP dispatch status {res.status_code}")
    except Exception as e:
        pending_requests.pop(request_id, None)
        logger.error("Failed to send checkout commit: %s", e)
        return False

    try:
        result = await asyncio.wait_for(future, timeout=15.0)
        logger.info(
            "Successfully received checkout confirmation for RequestID=%s.", request_id
        )
        return result
    except asyncio.TimeoutError:
        pending_requests.pop(request_id, None)
        logger.warning(
            "Timeout: Power Automate never responded for checkout RequestID=%s.",
            request_id,
        )
        return False
    except ValueError as e:
        logger.error("Data error in checkout for RequestID=%s: %s", request_id, e)
        return False


async def request_borrowed_items() -> (
    Optional[tuple[list[datetime], list[Status], list[int]]]
):
    """
    Requests a list of all currently borrowed items for reminder purposes.

    This function generates a unique request identifier and creates an asynchronous
    placeholder. It fires a POST request to trigger the borrowed items pipeline in
    Power Automate, and then pauses execution (for up to 15 seconds). Once the pipeline
    completes its search, it sends a webhook to the `/borrowed-items` endpoint,
    which correlates the ID and fulfills the placeholder with the lists of data.

    Returns
    -------
    Optional[tuple[list[datetime], list[Status], list[int]]]
        A tuple containing lists of all borrowed times, item statuses, and item IDs.
        Returns None if the request fails or times out.
    """
    request_id: str = str(uuid.uuid4())
    future: asyncio.Future = asyncio.get_running_loop().create_future()
    pending_requests[request_id] = future

    logger.info("Initiating request_borrowed_items (RequestID=%s).", request_id)

    try:
        headers = {
            "x-api-key": get_current_key(),
            "x-new-key": get_current_key(),
            "x-old-key": get_old_key(),
            "x-is-rotation": "true",
        }
        res = await requests.post(
            BORROWED_ITEMS_URL,
            json={"RequestID": request_id},
            headers=headers,
            timeout=TIMEOUT,
        )
        if res.status_code not in (200, 202):
            raise ValueError(f"HTTP dispatch status {res.status_code}")
    except Exception as e:
        pending_requests.pop(request_id, None)
        logger.error("Failed to send request_borrowed_items: %s", e)
        return None

    try:
        result = await asyncio.wait_for(future, timeout=15.0)
        logger.info(
            "Successfully received borrowed items list for RequestID=%s.", request_id
        )
        return result
    except asyncio.TimeoutError:
        pending_requests.pop(request_id, None)
        logger.warning(
            "Timeout: Power Automate never responded for request_borrowed_items RequestID=%s.",
            request_id,
        )
        return None
    except ValueError as e:
        logger.error(
            "Data error in request_borrowed_items for RequestID=%s: %s", request_id, e
        )
        return None


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
    now = datetime.now()
    cache = sheet_cache["intro"]
    if cache["data"] is not None and cache["timestamp"] is not None:
        if (now - cache["timestamp"]).total_seconds() < DAY_IN_SECONDS:
            logger.info("Using cached intro-sheet data.")
            return cache["data"]

    request_id: str = str(uuid.uuid4())
    future: asyncio.Future = asyncio.get_running_loop().create_future()
    pending_requests[request_id] = future

    logger.info("Initiating gather_intro_data (RequestID=%s).", request_id)
    try:
        headers = {"x-api-key": get_current_key()}
        res = await requests.post(
            INTRO_URL, json={"RequestID": request_id}, headers=headers, timeout=TIMEOUT
        )
        if res.status_code not in (200, 202):
            raise ValueError(f"HTTP dispatch status {res.status_code}")
    except Exception as e:
        pending_requests.pop(request_id, None)
        logger.error("Failed to send gather_intro_data: %s", e)
        return None

    try:
        result = await asyncio.wait_for(future, timeout=15.0)
        logger.info(
            "Successfully received intro-sheet data for RequestID=%s.", request_id
        )
        sheet_cache["intro"]["data"] = result
        sheet_cache["intro"]["timestamp"] = datetime.now()
        return result
    except asyncio.TimeoutError:
        pending_requests.pop(request_id, None)
        logger.warning(
            "Timeout: Power Automate never responded for gather_intro_data RequestID=%s.",
            request_id,
        )
        return None
    except ValueError as e:
        logger.error(
            "Data error in gather_intro_data for RequestID=%s: %s", request_id, e
        )
        return None


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
    now = datetime.now()
    cache = sheet_cache["303"]
    if cache["data"] is not None and cache["timestamp"] is not None:
        if (now - cache["timestamp"]).total_seconds() < DAY_IN_SECONDS:
            logger.info("Using cached 303-sheet data.")
            return cache["data"]

    request_id: str = str(uuid.uuid4())
    future: asyncio.Future = asyncio.get_running_loop().create_future()
    pending_requests[request_id] = future

    logger.info("Initiating gather_303_data (RequestID=%s).", request_id)
    try:
        headers = {"x-api-key": get_current_key()}
        res = await requests.post(
            ELEC_URL, json={"RequestID": request_id}, headers=headers, timeout=TIMEOUT
        )
        if res.status_code not in (200, 202):
            raise ValueError(f"HTTP dispatch status {res.status_code}")
    except Exception as e:
        pending_requests.pop(request_id, None)
        logger.error("Failed to send gather_303_data: %s", e)
        return None

    try:
        result = await asyncio.wait_for(future, timeout=15.0)
        logger.info(
            "Successfully received 303-sheet data for RequestID=%s.", request_id
        )
        sheet_cache["303"]["data"] = result
        sheet_cache["303"]["timestamp"] = datetime.now()
        return result
    except asyncio.TimeoutError:
        pending_requests.pop(request_id, None)
        logger.warning(
            "Timeout: Power Automate never responded for gather_303_data RequestID=%s.",
            request_id,
        )
        return None
    except ValueError as e:
        logger.error(
            "Data error in gather_303_data for RequestID=%s: %s", request_id, e
        )
        return None
