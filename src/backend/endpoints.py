"""
How all of the local endpoints function, and store data on the storage singletons.
"""

from datetime import datetime

from flask import Flask, jsonify, request, Response

from backend.singleton_storage import (
    BorrowedItemsStorage,
    CheckoutStorage,
    ItemStorage,
    NameStorage,
)
from backend.backend_types import Status
from backend.requests import get_item

flask_app: Flask = Flask(__name__)


@flask_app.route("/checkout", methods=["POST"])
def checkout() -> Response:
    """
    The checkout route.

    When this endpoint is accessed, it will be receiving data
    from the checkout pipeline in our databases.
    """

    checkout_storage_singleton = CheckoutStorage()
    checkout_storage_singleton.has_been_sent = request.get_json()["Sent"] == "Received"
    checkout_storage_singleton.on_change = True

    return jsonify([])


@flask_app.route("/items", methods=["POST"])
def get_item_route() -> Response:
    """
    The item route.

    When this endpoint is accessed, it will be receiving the item
    data that was requested.
    """

    item_name: str = request.get_json()["Item Name"]

    item_singleton: ItemStorage = ItemStorage()

    item_singleton.provide_data(item_name=item_name)
    item_singleton.on_change = True

    return jsonify([])


@flask_app.route("/names", methods=["POST"])
def get_name_route() -> Response:
    """
    The name route.

    When this endpoint is accessed, it will be receiving the first name,
    last name and email from a previous request.
    """

    payload: dict = request.get_json()

    first_name: str = payload["First Name"]
    last_name: str = payload["Last Name"]
    email: str = payload["Email"]
    excel_data: list[dict] = payload["excelData"]

    borrowed_items: list[str] = []
    time_borrowed: list[datetime] = []

    for i, row in enumerate(excel_data):
        borrowed_items[i] = get_item(row["Item ID"])

        date_string = row["Date Borrowed"]
        time_borrowed[i] = datetime.fromisoformat(date_string.replace("Z", "+00:00"))

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


@flask_app.route("/borrowed-items", methods=["GET"])
def request_borrowed_items() -> Response:
    """
    The borrowed items route.

    When this endpoint is accessed, it will be receiving the user info
    for all of the items that are currently borrowed, for reminder
    purposes.
    """

    payload = request.get_json()
    excel_data: list[dict] = payload["excelData"]

    borrowed_items: list[str] = []
    time_borrowed: list[datetime] = []
    statuses: list[Status] = []

    for i, row in enumerate(excel_data):
        borrowed_items[i] = get_item(row["Item ID"])

        date_string = row["Date Borrowed"]
        time_borrowed[i] = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        status_str = row["Status"]
        match status_str:
            case Status.INSTOCK:
                statuses[i] = Status.INSTOCK
            case Status.MISSING:
                statuses[i] = Status.MISSING
            case Status.BORROWED:
                statuses[i] = Status.BORROWED
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
