"""
This includes functions for sending requests to our database pipeline.
All returns get handled at our endpoints.
"""

import asyncio
from typing import Any
from datetime import datetime

import requests_async as requests

from backend.backend_constants import (
    CHECKOUT_URL,
    ITEM_URL,
    NAME_URL,
    BORROWED_ITEMS_URL,
    TIMEOUT,
    db_to_class_conversion,
)
from backend.backend_types import Status
from backend.singleton_storage import (
    NameStorage,
    ItemStorage,
    CheckoutStorage,
    BorrowedItemsStorage,
)

pipeline_lock: asyncio.Lock = asyncio.Lock()


async def get_name(barcode: str) -> tuple[str, str, str, list[str], list[datetime]]:
    """
    Gathers the name attached to a given barcode.

    Given a barcode, send a POST request to an database. Once requested,
    it will send back a first name and last name.

    Parameters
    ----------
    barcode : str
        The barcode attached to the name.

    Returns
    -------
    tuple[str, str, str, list[str], list[datetime]]
        A tuple of the first name, last name, their email, the items they
        have currently borrowed and the time they borrowed them.
    """
    async with pipeline_lock:
        send_json: dict[str, str] = {"Barcode": barcode}
        storage = NameStorage()
        storage.on_change = False  # Reset state before requesting

        try:
            res = await requests.post(NAME_URL, json=send_json, timeout=TIMEOUT)
            if res.status_code not in (200, 202):
                raise ValueError("Something did not send.")
        except ValueError as e:
            print(f"Error: {e}")
            return ("", "", "", [], [])

        timeout_counter = 0
        while not storage.on_change:
            if timeout_counter >= 150:  # 15 seconds (150 * 0.1s)
                print("Timeout: Power Automate never responded.")
                return ("", "", "", [], [])  # Return empty/safe defaults

            await asyncio.sleep(0.1)
            timeout_counter += 1

        storage.on_change = False
        return (
            storage.first_name,
            storage.last_name,
            storage.email,
            storage.borrowed_items,
            storage.time_borrowed,
        )


async def get_item(barcode: int) -> str:
    """
    Gathers the item name attached to a given barcode.

    Given a barcode, send a POST request to a database. Once requested,
    it will send back the name of the item attached to that barcode.

    Parameters
    ----------
    barcode : int
        The barcode attached to the item.

    Returns
    -------
    str
        The name of the item.
    """
    send_json: dict[str, int] = {"Item ID": barcode}
    storage = ItemStorage()
    storage.on_change = False

    try:
        res = await requests.post(ITEM_URL, json=send_json, timeout=TIMEOUT)
        if res.status_code not in (200, 202):
            raise ValueError("Something did not send.")
    except ValueError as e:
        print(f"Error: {e}")
        return ""

    timeout_counter = 0
    while not storage.on_change:
        if timeout_counter >= 150:
            print("Timeout: Power Automate never responded.")
            return ""

        await asyncio.sleep(0.1)
        timeout_counter += 1

    storage.on_change = False
    return storage.item_name


async def checkout(user_info: dict[str, Any]) -> bool:
    """
    From a given set of data representing the user info for a checkout,
    add that checkout to the database, and return the list of other
    checkouts that the user has.

    Given a user info dictionary containing the first and last name of the user,
    their barcode ID, their email, the item that they want to checkout,
    the current date in which they are checking out, and the status of the item,
    send a POST request of this data to the checkout database and validate whether
    this checkout is a return or a checkout.

    Parameters
    ----------
    user_info : dict[str, str  |  int  |  datetime]
        Info of the user for their checkout.
        Structure:
        {
            "First Name": str
            "Last Name": str
            "ID": str - A set of numbers and letters.
            "Email": str
            "Item ID": int - A set of 5 numbers.
            "Date Borrowed": datetime - The date and time the user borrowed the item.
            "Status": Status (StrEnum) (Borrowed, In Stock, Missing)
        }
    """
    send_json: dict = {
        "First Name": "",
        "Last Name": "",
        "ID": "",
        "Email": "",
        "Item ID": 0,
        "Date Borrowed": "",
        "Status": "",
    }

    for key in send_json:
        user_info_key: str = db_to_class_conversion[key]
        match user_info[user_info_key]:
            case datetime():
                send_json[key] = user_info[user_info_key].strftime("%Y-%m-%dT%H:%M:%SZ")
            case str() | int():
                send_json[key] = user_info[user_info_key]
            case Status():
                send_json[key] = user_info[user_info_key].value

    storage = CheckoutStorage()
    storage.on_change = False

    try:
        res = await requests.post(CHECKOUT_URL, json=send_json, timeout=TIMEOUT)
        if res.status_code not in (200, 202):
            raise ValueError("Something did not send.")
    except ValueError as e:
        print(f"Error: {e}")
        return False

    timeout_counter = 0
    while not storage.on_change:
        if timeout_counter >= 150:
            print("Timeout: Power Automate never responded.")
            return False

        await asyncio.sleep(0.1)
        timeout_counter += 1

    storage.on_change = False
    return storage.has_been_sent


async def request_borrowed_items() -> tuple[list[str], list[datetime], list[Status]]:
    """
    Requests a list of all of the borrowed items.

    Requests a list of all of the currently borrowed items for reminder purposes.
    Will send a GET request to our database pipeline, which will then separately be received.

    Returns
    -------
    list[tuple[Any]]
        A list of the sets of borrowed items and the person currently loaning them, to then
        remind them.
    """
    storage = BorrowedItemsStorage()
    storage.on_change = False

    try:
        res = await requests.get(BORROWED_ITEMS_URL, timeout=TIMEOUT)
        if res.status_code not in (200, 202):
            raise ValueError("Something did not send.")
    except ValueError as e:
        print(f"Error: {e}")
        return ([], [], [])

    timeout_counter = 0
    while not storage.on_change:
        if timeout_counter >= 150:
            print("Timeout: Power Automate never responded.")
            return ([], [], [])

        await asyncio.sleep(0.1)
        timeout_counter += 1

    storage.on_change = False
    return (storage.borrowed_items, storage.time_borrowed, storage.statuses)
