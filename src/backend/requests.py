"""
This includes functions for sending requests to our database pipeline.
The functions wait for incoming data which is received and matched up at our endpoints.
"""

import asyncio
from datetime import datetime

import requests_async as requests

from backend.backend_constants import (
    CHECKOUT_URL,
    ITEM_URL,
    NAME_URL,
    BORROWED_ITEMS_URL,
    TIMEOUT,
    to_excel_date,
    db_to_class_conversion,
)
from backend.app_state import pending_requests
from backend.backend_types import Status, UserInfoPayload
import uuid
from typing import Optional


async def get_name(
    barcode: str,
) -> Optional[tuple[str, str, list[datetime], list[Status], list[int]]]:
    """
    Gathers the name and currently borrowed items attached to a given barcode.

    This function generates a unique request identifier and creates an asynchronous 
    placeholder. It sends a POST request to the Power Automate pipeline, passing along 
    both the barcode and the unique ID. It then pauses execution (for up to 15 seconds) 
    until the `/names` endpoint receives the matching webhook callback and fulfills 
    the placeholder with the requested data.

    Parameters
    ----------
    barcode : str
        The barcode attached to the name.

    Returns
    -------
    Optional[tuple[str, str, list[datetime], list[Status], list[int]]]
        A tuple of the user's name, their email, the times they borrowed items,
        the statuses of those items, and the item IDs. Returns None if the 
        request fails or times out.
    """
    request_id: str = str(uuid.uuid4())
    send_json: dict[str, str] = {"UserID": barcode, "RequestID": request_id}

    future: asyncio.Future = asyncio.get_running_loop().create_future()
    pending_requests[request_id] = future

    try:
        res = await requests.post(NAME_URL, json=send_json, timeout=TIMEOUT)
        if res.status_code not in (200, 202):
            raise ValueError("Something did not send.")
    except ValueError as e:
        pending_requests.pop(request_id, None)
        print(f"Error: {e}")
        return None

    try:
        return await asyncio.wait_for(future, timeout=15.0)
    except asyncio.TimeoutError:
        pending_requests.pop(request_id, None)
        print("Timeout: Power Automate never responded.")
        return None
    except ValueError as e:
        print(f"Data Error: {e}")
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

    try:
        res = await requests.post(ITEM_URL, json=send_json, timeout=TIMEOUT)
        if res.status_code not in (200, 202):
            raise ValueError("Something did not send.")
    except ValueError as e:
        pending_requests.pop(request_id, None)
        print(f"Error: {e}")
        return None

    try:
        return await asyncio.wait_for(future, timeout=15.0)
    except asyncio.TimeoutError:
        pending_requests.pop(request_id, None)
        print("Timeout: Power Automate never responded.")
        return None
    except ValueError as e:
        print(f"Data Error: {e}")
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
            "UserID": str - A set of numbers and letters.
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
        "UserID": "",
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

    try:
        res = await requests.post(CHECKOUT_URL, json=send_json, timeout=TIMEOUT)
        if res.status_code not in (200, 202):
            raise ValueError("Something did not send.")
    except ValueError as e:
        pending_requests.pop(request_id, None)
        print(f"Error: {e}")
        return False

    try:
        return await asyncio.wait_for(future, timeout=15.0)
    except asyncio.TimeoutError:
        pending_requests.pop(request_id, None)
        print("Timeout: Power Automate never responded.")
        return False
    except ValueError as e:
        print(f"Data Error: {e}")
        return False


async def request_borrowed_items() -> Optional[tuple[list[datetime], list[Status], list[int]]]:
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

    try:
        res = await requests.post(BORROWED_ITEMS_URL, json={"RequestID": request_id}, timeout=TIMEOUT)
        if res.status_code not in (200, 202):
            raise ValueError("Something did not send.")
    except ValueError as e:
        pending_requests.pop(request_id, None)
        print(f"Error: {e}")
        return None

    try:
        return await asyncio.wait_for(future, timeout=15.0)
    except asyncio.TimeoutError:
        pending_requests.pop(request_id, None)
        print("Timeout: Power Automate never responded.")
        return None
    except ValueError as e:
        print(f"Data Error: {e}")
        return None
