"""
This includes functions for sending requests to our database pipeline.
All returns get handled at our endpoints.
"""

from typing import Any
from datetime import datetime

from backend.backend_constants import CHECKOUT_URL, ITEM_URL, NAME_URL


def get_name(barcode: str) -> tuple[str, str, str]:
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
    tuple[str, str, str]
        A tuple of the first name, last name and their email.
    """
    ...


def get_item(barcode: int) -> str:
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
    ...


def checkout(
    user_info: dict[str, str | int | datetime],
) -> list[tuple[str, datetime]]:
    """
    From a given set of data representing the user info for a checkout,
    add that checkout to the database, and return the list of other
    checkouts that the user has.

    Given a user info dictionary containing the first and last name of the user,
    their barcode ID, their email, the item that they want to checkout,
    the current date in which they are checking out, and the status of the item,
    send a POST request of this data to the checkout database and validate whether
    this checkout is a return or a checkout. The database will then return all of
    the checkouts that the user currently has to make the user aware if they are
    still holding any items. This does not include items that are marked as lost.

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
            "Status": str - borrowed, in stock, missing
        }

    Returns
    -------
    list[tuple[str, datetime]]
        A list of tuples with a given item that the user currently
        has borrowed and the time that they borrowed it.
    """
    ...


def request_borrowed_items() -> list[tuple[Any]]:
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
    ...
