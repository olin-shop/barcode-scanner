"""
How all of the local endpoints function, receiving webhook callbacks
and matching them back to their original pending requests.
"""

import logging
from datetime import datetime
from typing import Optional, Any

import pandas as pd
from quart import Quart, request, Response, jsonify, abort

from backend.backend_types import Status
from backend.backend_constants import from_excel_date, EMPTY_DATA
from backend.app_state import pending_requests
from backend.api_security import get_current_key

logger = logging.getLogger(__name__)

quart_app: Quart = Quart(__name__)


def _fulfill_pending_future(
    request_id: Optional[str], result: Any = None, exception: Optional[Exception] = None
) -> bool:
    """Safely fulfills a pending asyncio Future across event loops / threads."""
    if not request_id or request_id not in pending_requests:
        return False
    fut = pending_requests.pop(request_id)
    if fut.done():
        return False

    loop = fut.get_loop()
    if exception is not None:
        loop.call_soon_threadsafe(fut.set_exception, exception)
    else:
        loop.call_soon_threadsafe(fut.set_result, result)
    return True


@quart_app.before_request
async def verify_api_key():
    """
    Validates the x-api-key header on all incoming webhook requests.
    Aborts the request with 401 Unauthorized if the key is missing or invalid.
    """
    if request.method == "POST":
        api_key = request.headers.get("x-api-key")
        if not api_key or api_key != get_current_key():
            logger.warning(
                "Unauthorized webhook access attempt from %s. Invalid x-api-key.",
                request.remote_addr,
            )
            abort(401, description="Unauthorized")


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

    logger.info(
        "Received /checkout webhook callback (RequestID=%s, Sent=%s).",
        request_id,
        has_been_sent,
    )

    if _fulfill_pending_future(request_id, result=has_been_sent):
        logger.debug("Successfully fulfilled pending request RequestID=%s", request_id)
    else:
        logger.warning(
            "Received /checkout callback for unknown or expired RequestID=%s",
            request_id,
        )

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

    logger.info(
        "Received /items webhook callback (RequestID=%s, ItemName=%r).",
        request_id,
        item_name,
    )

    try:
        item_status: Status = Status(raw_status)
    except ValueError:
        item_status = Status.NONE
        logger.error(
            "Invalid or unrecognized ItemStatus=%r for item %r (RequestID=%s)",
            raw_status,
            item_name,
            request_id,
        )

    if _fulfill_pending_future(request_id, result=(item_name, item_status)):
        logger.debug("Successfully fulfilled pending request RequestID=%s", request_id)
    else:
        logger.warning(
            "Received /items callback for unknown or expired RequestID=%s", request_id
        )

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

    logger.info(
        "Received /names webhook callback (RequestID=%s, Name=%r, ItemsCount=%d).",
        request_id,
        name,
        len(excel_data),
    )

    time_borrowed: list[datetime] = []
    statuses: list[Status] = []
    item_ids: list[int] = []

    for row in excel_data:
        try:
            item_id: int = int(row.get("ItemID", 0))
            date_number: float = float(row.get("DateBorrowed", 0.0))
            status: Status = Status(row.get("ItemStatus", ""))

            if status == Status.NONE:
                logger.error(
                    "Invalid status NONE for item_id=%d in /names payload (RequestID=%s)",
                    item_id,
                    request_id,
                )

            item_ids.append(item_id)
            time_borrowed.append(from_excel_date(date_number))
            statuses.append(status)
        except (ValueError, KeyError, TypeError) as e:
            logger.error(
                "Corrupted row data in /names callback for RequestID=%s: %s",
                request_id,
                e,
            )
            _fulfill_pending_future(
                request_id, exception=ValueError(f"Corrupted row data: {e}")
            )
            return jsonify(EMPTY_DATA)

    if _fulfill_pending_future(
        request_id, result=(name, email, time_borrowed, statuses, item_ids)
    ):
        logger.debug("Successfully fulfilled pending request RequestID=%s", request_id)
    else:
        logger.warning(
            "Received /names callback for unknown or expired RequestID=%s", request_id
        )

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

    logger.info(
        "Received /borrowed-items webhook callback (RequestID=%s, ItemsCount=%d).",
        request_id,
        len(excel_data),
    )

    time_borrowed: list[datetime] = []
    statuses: list[Status] = []
    item_ids: list[int] = []

    for row in excel_data:
        try:
            item_id: int = int(row.get("ItemID", 0))
            date_number: float = float(row.get("DateBorrowed", 0.0))
            status: Status = Status(row.get("ItemStatus", ""))

            if status == Status.NONE:
                logger.error(
                    "Invalid status NONE for item_id=%d in /borrowed-items payload (RequestID=%s)",
                    item_id,
                    request_id,
                )

            item_ids.append(item_id)
            time_borrowed.append(from_excel_date(date_number))
            statuses.append(status)
        except (ValueError, KeyError, TypeError) as e:
            logger.error(
                "Corrupted row data in /borrowed-items callback for RequestID=%s: %s",
                request_id,
                e,
            )
            _fulfill_pending_future(
                request_id, exception=ValueError(f"Corrupted row data: {e}")
            )
            return jsonify(EMPTY_DATA)

    if _fulfill_pending_future(request_id, result=(time_borrowed, statuses, item_ids)):
        logger.debug("Successfully fulfilled pending request RequestID=%s", request_id)
    else:
        logger.warning(
            "Received /borrowed-items callback for unknown or expired RequestID=%s",
            request_id,
        )

    return jsonify(EMPTY_DATA)


@quart_app.route("/intro-sheet", methods=["POST"])
async def intro_sheet_route() -> Response:
    """
    Receives the intro sheet data from the pipeline webhook.
    Converts the excelData list of dicts to a pandas DataFrame and fulfills the pending request.
    """
    payload: dict = await request.get_json()
    request_id: Optional[str] = payload.get("RequestID")
    excel_data: list[dict] = payload.get("excelData", [])

    logger.info(
        "Received /intro-sheet webhook callback (RequestID=%s, RowsCount=%d).",
        request_id,
        len(excel_data),
    )

    try:
        df = pd.DataFrame(excel_data)
        if _fulfill_pending_future(request_id, result=df):
            logger.debug(
                "Successfully fulfilled pending request RequestID=%s", request_id
            )
        else:
            logger.warning(
                "Received /intro-sheet callback for unknown or expired RequestID=%s",
                request_id,
            )
    except Exception as e:
        logger.error(
            "Failed to parse intro-sheet data for RequestID=%s: %s", request_id, e
        )
        _fulfill_pending_future(request_id, exception=e)

    return jsonify(EMPTY_DATA)


@quart_app.route("/303-sheet", methods=["POST"])
async def sheet_303_route() -> Response:
    """
    Receives the 303 sheet data from the pipeline webhook.
    Converts the excelData list of dicts to a pandas DataFrame and fulfills the pending request.
    """
    payload: dict = await request.get_json()
    request_id: Optional[str] = payload.get("RequestID")
    excel_data: list[dict] = payload.get("excelData", [])

    logger.info(
        "Received /303-sheet webhook callback (RequestID=%s, RowsCount=%d).",
        request_id,
        len(excel_data),
    )

    try:
        df = pd.DataFrame(excel_data)
        if _fulfill_pending_future(request_id, result=df):
            logger.debug(
                "Successfully fulfilled pending request RequestID=%s", request_id
            )
        else:
            logger.warning(
                "Received /303-sheet callback for unknown or expired RequestID=%s",
                request_id,
            )
    except Exception as e:
        logger.error(
            "Failed to parse 303-sheet data for RequestID=%s: %s", request_id, e
        )
        _fulfill_pending_future(request_id, exception=e)

    return jsonify(EMPTY_DATA)
