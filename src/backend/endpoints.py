"""
How all of the local endpoints function, receiving webhook callbacks and matching them back to their original pending requests.
"""

import logging
from datetime import datetime
from typing import Optional

from quart import Quart, request, Response, jsonify

from backend.backend_types import Status
from backend.backend_constants import from_excel_date, EMPTY_DATA
from backend.app_state import pending_requests

logger = logging.getLogger(__name__)

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

    logger.info("Received /checkout webhook callback (RequestID=%s, Sent=%s).", request_id, has_been_sent)

    if request_id and request_id in pending_requests:
        pending_requests.pop(request_id).set_result(has_been_sent)
        logger.debug("Successfully fulfilled pending request RequestID=%s", request_id)
    else:
        logger.warning("Received /checkout callback for unknown or expired RequestID=%s", request_id)

    return jsonify(EMPTY_DATA)


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
    raw_status = payload.get("ItemStatus")

    logger.info("Received /items webhook callback (RequestID=%s, ItemName=%r).", request_id, item_name)

    try:
        item_status: Status = Status(raw_status)
    except ValueError:
        item_status = Status.NONE
        logger.error("Invalid or unrecognized ItemStatus=%r for item %r (RequestID=%s)", raw_status, item_name, request_id)

    if request_id and request_id in pending_requests:
        pending_requests.pop(request_id).set_result((item_name, item_status))
        logger.debug("Successfully fulfilled pending request RequestID=%s", request_id)
    else:
        logger.warning("Received /items callback for unknown or expired RequestID=%s", request_id)

    return jsonify(EMPTY_DATA)


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

    logger.info("Received /names webhook callback (RequestID=%s, Name=%r, ItemsCount=%d).", request_id, name, len(excel_data))

    time_borrowed: list[datetime] = []
    statuses: list[Status] = []
    item_ids: list[int] = []

    for row in excel_data:
        try:
            item_id: int = int(row.get("ItemID", 0))
            date_number: float = float(row.get("DateBorrowed", 0.0))
            status: Status = Status(row.get("ItemStatus", ""))
            
            if status == Status.NONE:
                logger.error("Invalid status NONE for item_id=%d in /names payload (RequestID=%s)", item_id, request_id)
                
            item_ids.append(item_id)
            time_borrowed.append(from_excel_date(date_number))
            statuses.append(status)
        except (ValueError, KeyError, TypeError) as e:
            logger.error("Corrupted row data in /names callback for RequestID=%s: %s", request_id, e)
            if request_id and request_id in pending_requests:
                pending_requests.pop(request_id).set_exception(ValueError(f"Corrupted row data: {e}"))
            return jsonify(EMPTY_DATA)

    if request_id and request_id in pending_requests:
        pending_requests.pop(request_id).set_result((name, email, time_borrowed, statuses, item_ids))
        logger.debug("Successfully fulfilled pending request RequestID=%s", request_id)
    else:
        logger.warning("Received /names callback for unknown or expired RequestID=%s", request_id)

    return jsonify(EMPTY_DATA)


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

    logger.info("Received /borrowed-items webhook callback (RequestID=%s, ItemsCount=%d).", request_id, len(excel_data))

    time_borrowed: list[datetime] = []
    statuses: list[Status] = []
    item_ids: list[int] = []

    for row in excel_data:
        try:
            item_id: int = int(row.get("ItemID", 0))
            date_number: float = float(row.get("DateBorrowed", 0.0))
            status: Status = Status(row.get("ItemStatus", ""))
            
            if status == Status.NONE:
                logger.error("Invalid status NONE for item_id=%d in /borrowed-items payload (RequestID=%s)", item_id, request_id)
                
            item_ids.append(item_id)
            time_borrowed.append(from_excel_date(date_number))
            statuses.append(status)
        except (ValueError, KeyError, TypeError) as e:
            logger.error("Corrupted row data in /borrowed-items callback for RequestID=%s: %s", request_id, e)
            if request_id and request_id in pending_requests:
                pending_requests.pop(request_id).set_exception(ValueError(f"Corrupted row data: {e}"))
            return jsonify(EMPTY_DATA)

    if request_id and request_id in pending_requests:
        pending_requests.pop(request_id).set_result((time_borrowed, statuses, item_ids))
        logger.debug("Successfully fulfilled pending request RequestID=%s", request_id)
    else:
        logger.warning("Received /borrowed-items callback for unknown or expired RequestID=%s", request_id)

    return jsonify(EMPTY_DATA)
