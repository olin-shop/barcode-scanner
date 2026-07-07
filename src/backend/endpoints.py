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
from backend.backend_constants import from_excel_date
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
    item_status: Status = Status.NONE

    match payload["Item Status"]:
        case Status.INSTOCK.value:
            item_status = Status.INSTOCK
        case Status.MISSING.value:
            item_status = Status.MISSING
        case Status.BORROWED.value:
            item_status = Status.BORROWED
        case Status.NONE.value:
            raise ValueError("Item is of unknown status!")
        case _:
            raise ValueError("Item is of unknown status!")

    item_singleton: ItemStorage = ItemStorage()
    item_singleton.provide_data(item_name=item_name, item_status=item_status)
    item_singleton.on_change = True

    return jsonify([])


@quart_app.route("/names", methods=["POST"])
async def get_name_route() -> Response:
    """
    The name route.

    When this endpoint is accessed, it will be receiving
    the name and email from a previous request. It will
    also receive the list of borrowed items associated
    with that name and the times that they were borrowed,
    along with the status of the item currently.
    """
    payload: dict = await request.get_json()

    name: str = payload["Name"]
    email: str = payload["Email"]
    excel_data: list[dict] = payload["excelData"]

    borrowed_items: list[str] = []
    time_borrowed: list[datetime] = []
    statuses: list[Status] = []

    for row in excel_data:
        item_name, item_status = await get_item(row["Item ID"])

        borrowed_items.append(item_name)
        statuses.append(item_status)
        date_number = row["Date Borrowed"]
        time_borrowed.append(
            from_excel_date(date_number)
            # datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        )  # change to number

    name_singleton: NameStorage = NameStorage()

    name_singleton.provide_data(
        name=name,
        email=email,
        borrowed_items=borrowed_items,
        time_borrowed=time_borrowed,
        statuses=statuses,
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
        item_name, _ = await get_item(row["Item ID"])
        borrowed_items.append(item_name)

        date_number = row["Date Borrowed"]
        time_borrowed.append(from_excel_date(date_number))
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
