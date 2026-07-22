"""
How all of the local endpoints function, receiving webhook callbacks and matching them back to their original pending requests.
"""

from datetime import datetime
from typing import Optional

from quart import Quart, request, Response

from backend.backend_types import Status
from backend.backend_constants import from_excel_date, EMPTY
from backend.app_state import pending_requests

quart_app: Quart = Quart(__name__)


@quart_app.route("/checkout", methods=["POST"])
async def checkout() -> Response:
    """
    The checkout route.

    Receives the checkout confirmation from the checkout pipeline webhook. 
    It extracts the unique request identifier from the payload, validates if the 
    transmission was successful, and uses it to fulfill the asynchronous placeholder. 
    This un-pauses the original `checkout()` request in `requests.py`.
    """
    payload: dict = await request.get_json()
    request_id: Optional[str] = payload.get("RequestID")

    has_been_sent: bool = payload.get("Sent") == "Received"
    if request_id and request_id in pending_requests:
        pending_requests.pop(request_id).set_result(has_been_sent)

    return EMPTY


@quart_app.route("/items", methods=["POST"])
async def get_item_route() -> Response:
    """
    The item route.

    Receives the item data from the item pipeline webhook. It parses the item name 
    and enum status, extracts the unique request identifier, and fulfills the 
    asynchronous placeholder to un-pause the original `get_item()` request.
    """
    payload: dict = await request.get_json()
    request_id: Optional[str] = payload.get("RequestID")
    item_name: str = payload.get("ItemName", "")
    item_status: Status = Status.NONE

    try:
        item_status = Status(payload.get("ItemStatus"))
    except ValueError:
        item_status = Status.NONE

    if item_status == Status.NONE:
        raise ValueError("Item is of unknown status!")

    if request_id and request_id in pending_requests:
        pending_requests.pop(request_id).set_result((item_name, item_status))

    return EMPTY


@quart_app.route("/names", methods=["POST"])
async def get_name_route() -> Response:
    """
    The name route.

    Receives the user data and borrowed items payload from the name pipeline webhook. 
    It parses the Excel dates into datetimes, maps the enum statuses, extracts the 
    unique request identifier, and fulfills the asynchronous placeholder to un-pause 
    the original `get_name()` request.
    """
    payload: dict = await request.get_json()
    request_id: Optional[str] = payload.get("RequestID")

    name: str = payload.get("Name", "")
    email: str = payload.get("Email", "")
    excel_data: list[dict] = payload.get("excelData", [])

    time_borrowed: list[datetime] = []
    statuses: list[Status] = []
    item_ids: list[int] = []

    for row in excel_data:
        item_ids.append(int(row["ItemID"]))
        
        try:
            status: Status = Status(row["ItemStatus"])
        except ValueError:
            status = Status.NONE
            
        statuses.append(status)
                
        date_number: float = float(row["DateBorrowed"])
        
        time_borrowed.append(from_excel_date(date_number))

    if request_id and request_id in pending_requests:
        pending_requests.pop(request_id).set_result((name, email, time_borrowed, statuses, item_ids))

    return EMPTY


@quart_app.route("/borrowed-items", methods=["POST"])
async def request_borrowed_items_route() -> Response:
    """
    The borrowed items route.

    Receives the full list of currently borrowed items from the pipeline webhook. 
    It parses the dates and statuses, extracts the unique request identifier, and 
    fulfills the asynchronous placeholder to un-pause the original 
    `request_borrowed_items()` request.
    """
    payload: dict = await request.get_json()
    request_id: Optional[str] = payload.get("RequestID")
    excel_data: list[dict] = payload.get("excelData", [])

    time_borrowed: list[datetime] = []
    statuses: list[Status] = []
    item_ids: list[int] = []

    for row in excel_data:
        item_ids.append(int(row["ItemID"]))

        date_number: float = float(row["DateBorrowed"])
        time_borrowed.append(from_excel_date(date_number))
        status_str: str = row["ItemStatus"]

        try:
            status: Status = Status(status_str)
        except ValueError:
            status = Status.NONE

        if status == Status.NONE:
            raise ValueError("Supposed to be one of these three, check the Excel sheet for errors.")
            
        statuses.append(status)

    if request_id and request_id in pending_requests:
        pending_requests.pop(request_id).set_result((time_borrowed, statuses, item_ids))

    return EMPTY
