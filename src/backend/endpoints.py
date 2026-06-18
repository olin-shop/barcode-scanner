"""
How all of the local endpoints function, and store data on the storage singletons.
"""

from datetime import datetime

from quart import Quart, jsonify, request, Response

from backend.singleton_storage import (
    BorrowedItemsStorage,
    CheckoutStorage,
    ItemStorage,
    NameStorage,
)
from backend.backend_types import Status
from backend.requests import get_item

quart_app: Quart = Quart(__name__)


@quart_app.route("/checkout", methods=["POST"])
async def checkout() -> Response:
    """
    The checkout route.

    When this endpoint is accessed, it will be receiving data
    from the checkout pipeline in our databases.
    """
    payload = await request.get_json()

    checkout_storage_singleton = CheckoutStorage()
    checkout_storage_singleton.has_been_sent = payload["Sent"] == "Received"
    checkout_storage_singleton.on_change = True

    return jsonify([])


@quart_app.route("/items", methods=["POST"])
async def get_item_route() -> Response:
    """
    The item route.

    When this endpoint is accessed, it will be receiving the item
    data that was requested.
    """
    payload = await request.get_json()
    item_name: str = payload["Item Name"]

    item_singleton: ItemStorage = ItemStorage()
    item_singleton.provide_data(item_name=item_name)
    item_singleton.on_change = True

    return jsonify([])


@quart_app.route("/names", methods=["POST"])
async def get_name_route() -> Response:
    """
    The name route.

    When this endpoint is accessed, it will be receiving the first name,
    last name and email from a previous request.
    """
    payload: dict = await request.get_json()

    first_name: str = payload["First Name"]
    last_name: str = payload["Last Name"]
    email: str = payload["Email"]
    excel_data: list[dict] = payload["excelData"]

    borrowed_items: list[str] = []
    time_borrowed: list[datetime] = []

    for row in excel_data:
        # Await the request function here to yield back to the event loop
        borrowed_items.append(await get_item(row["Item ID"]))

        date_string = row["Date Borrowed"]
        time_borrowed.append(datetime.fromisoformat(date_string.replace("Z", "+00:00")))

    name_singleton: NameStorage = NameStorage()

    name_singleton.provide_data(
        first_name=first_name,
        last_name=last_name,
        email=email,
        borrowed_items=borrowed_items,
        time_borrowed=time_borrowed,
    )
    name_singleton.on_change = True

    return jsonify([])


@quart_app.route("/borrowed-items", methods=["GET", "POST"])
async def request_borrowed_items_route() -> Response:
    """
    The borrowed items route.

    When this endpoint is accessed, it will be receiving the user info
    for all of the items that are currently borrowed, for reminder
    purposes.
    """
    payload = await request.get_json()
    excel_data: list[dict] = payload["excelData"]

    borrowed_items: list[str] = []
    time_borrowed: list[datetime] = []
    statuses: list[Status] = []

    for row in excel_data:
        borrowed_items.append(await get_item(row["Item ID"]))

        date_string = row["Date Borrowed"]
        time_borrowed.append(datetime.fromisoformat(date_string.replace("Z", "+00:00")))
        status_str = row["Status"]

        match status_str:
            case Status.INSTOCK:
                statuses.append(Status.INSTOCK)
            case Status.MISSING:
                statuses.append(Status.MISSING)
            case Status.BORROWED:
                statuses.append(Status.BORROWED)
            case _:
                raise ValueError(
                    "Supposed to be one of these three, check the Excel sheet for errors."
                )

        borrowed_items_singleton = BorrowedItemsStorage()

        borrowed_items_singleton.provide_data(
            borrowed_items=borrowed_items,
            time_borrowed=time_borrowed,
            statuses=statuses,
        )
        borrowed_items_singleton.on_change = True

    return jsonify([])
