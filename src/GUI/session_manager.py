"""
per-user session state and backend communication for the kiosk app.

"""

import logging
from datetime import datetime

from backend.backend_constants import min_datetime
from backend.backend_types import BorrowedItem, Status, UserInfoPayload, to_item_id
from backend.requests import checkout as backend_checkout
from backend.requests import get_item, get_name

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Owns the state for a single active user session and provides the
    backend hooks the GUI calls into.

    The GUI layer only ever talks to the public (non-underscore) methods
    below, never to backend.requests directly.
    """

    def __init__(self) -> None:
        self.current_user_barcode: str | None = None
        self.current_user_name: str = ""
        self.current_user_email: str = ""
        self.user_items: list[BorrowedItem] = []

    # ---- Session lifecycle -------------------------------------------------

    def reset(self) -> None:
        """Clear all session state, ready for the next user."""
        logger.info("Resetting session (previous user=%s)", self.current_user_barcode)
        self.current_user_barcode = None
        self.current_user_name = ""
        self.current_user_email = ""
        self.user_items = []

    # ---- ID scan -------------------------------------------------------------

    async def start_session(self, user_barcode: str) -> list[BorrowedItem]:
        """Called after a user ID is scanned. Loads and caches their items."""
        self.current_user_barcode = user_barcode
        self.user_items = await self._backend_get_user_items(user_barcode)
        return self.user_items

    # ---- Item scan -----------------------------------------------------------

    async def lookup_item(self, item_barcode: str) -> tuple[str, bool]:
        """
        Returns (item_name, is_borrowed) for a scanned item barcode,
        checked against the current session's borrowed items.
        """
        return await self._backend_lookup_item(item_barcode, self.user_items)

    async def confirm_borrow(self, item_barcode: str, item_name: str) -> bool:
        """Confirm a new borrow and, on success, add it to the session's item list."""
        success = await self._backend_confirm_borrow(
            self.current_user_barcode, item_barcode, item_name
        )
        if success:
            self.user_items.append(BorrowedItem(item_name, item_barcode, datetime.now()))
        return success

    async def confirm_return(self, item_barcode: str, item_name: str) -> bool:
        """Confirm a return and, on success, drop it from the session's item list."""
        success = await self._backend_confirm_return(
            self.current_user_barcode, item_barcode, item_name
        )
        if success:
            self.user_items = [i for i in self.user_items if i.name != item_name]
        return success

    async def mark_missing(self, item_barcode: str, item_name: str) -> bool:
        """Mark an item missing and, on success, drop it from the session's item list."""
        success = await self._backend_mark_missing(
            self.current_user_barcode, item_barcode, item_name
        )
        if success:
            self.user_items = [i for i in self.user_items if i.name != item_name]
        return success

    # =====================================================================
    # BACKEND HOOKS
    # Real logic: talks to the database pipeline via backend/requests.py.
    # =====================================================================

    async def _backend_get_user_items(self, user_barcode: str) -> list[BorrowedItem]:
        """
        Called after a user ID is scanned.

        Looks the user up (name/email + their raw item ids/dates/statuses),
        then resolves each currently-BORROWED item id to a human-readable
        name. Returns an empty list if the user has no borrowed items, or
        isn't found at all.
        """
        name, email, time_borrowed, statuses, item_ids = await get_name(user_barcode)
        self.current_user_name = name
        self.current_user_email = email

        if not item_ids:
            logger.info("No borrowed items found for user=%s", user_barcode)
            return []

        items: list[BorrowedItem] = []
        for item_id, borrowed_at, status in zip(item_ids, time_borrowed, statuses):
            if status != Status.BORROWED:
                continue

            item_name, _status = await get_item(item_id)
            if not item_name:
                logger.warning("Could not resolve item id=%s for user=%s", item_id, user_barcode)
                item_name = f"Item ({item_id})"

            items.append(BorrowedItem(item_name, str(item_id), borrowed_at))

        return items

    async def _backend_lookup_item(
        self, item_barcode: str, user_items: list[BorrowedItem]
    ) -> tuple[str, bool]:
        """
        Called when an item barcode is scanned on the BorrowedItemsPage.

        Returns
        -------
        tuple[str, bool]
            (item_name, is_borrowed) where is_borrowed True means the item
            is already borrowed by this user (-> return flow), and False
            means it's new (-> borrow flow).
        """
        # Fast path: we already know this item is borrowed by this user
        # this session, no need to round-trip to the backend.
        for item in user_items:
            if item.barcode == item_barcode:
                return item.name, True

        item_id = to_item_id(item_barcode)
        if item_id is None:
            logger.warning("Received a non-numeric item barcode: %r", item_barcode)
            return f"Item ({item_barcode})", False

        item_name, status = await get_item(item_id)
        if not item_name:
            logger.warning("Unknown item barcode scanned: %s", item_barcode)
            return f"Item ({item_barcode})", False

        return item_name, status == Status.BORROWED

    async def _backend_confirm_borrow(
        self, user_barcode: str | None, item_barcode: str, item_name: str
    ) -> bool:
        """Called when the user confirms borrowing a new item."""
        item_id = to_item_id(item_barcode)
        if item_id is None or user_barcode is None:
            logger.error(
                "Cannot confirm borrow - invalid barcode(s): user=%s item=%s",
                user_barcode, item_barcode,
            )
            return False

        payload: UserInfoPayload = {
            "name": self.current_user_name,
            "user_id": user_barcode,
            "email": self.current_user_email,
            "item_id": item_id,
            "borrowed_date": datetime.now(),
            "returned_date": min_datetime,
            "item_status": Status.BORROWED,
        }
        success = await backend_checkout(payload)

        if success:
            logger.info(
                "Borrow confirmed: user=%s, item=%s (%s)", user_barcode, item_barcode, item_name
            )
        else:
            logger.error(
                "Borrow failed to send: user=%s, item=%s (%s)", user_barcode, item_barcode, item_name
            )
        return success

    async def _backend_confirm_return(
        self, user_barcode: str | None, item_barcode: str, item_name: str
    ) -> bool:
        """Called when the user confirms returning a borrowed item."""
        item_id = to_item_id(item_barcode)
        if item_id is None or user_barcode is None:
            logger.error(
                "Cannot confirm return - invalid barcode(s): user=%s item=%s",
                user_barcode, item_barcode,
            )
            return False

        borrowed_at = next(
            (i.borrowed_at for i in self.user_items if i.barcode == item_barcode), min_datetime
        )

        payload: UserInfoPayload = {
            "name": self.current_user_name,
            "user_id": user_barcode,
            "email": self.current_user_email,
            "item_id": item_id,
            "borrowed_date": borrowed_at,
            "returned_date": datetime.now(),
            "item_status": Status.INSTOCK,
        }
        success = await backend_checkout(payload)

        if success:
            logger.info(
                "Return confirmed: user=%s, item=%s (%s)", user_barcode, item_barcode, item_name
            )
        else:
            logger.error(
                "Return failed to send: user=%s, item=%s (%s)", user_barcode, item_barcode, item_name
            )
        return success

    async def _backend_mark_missing(
        self, user_barcode: str | None, item_barcode: str, item_name: str
    ) -> bool:
        """Called when the user marks a borrowed item as missing."""
        item_id = to_item_id(item_barcode)
        if item_id is None or user_barcode is None:
            logger.error(
                "Cannot mark missing - invalid barcode(s): user=%s item=%s",
                user_barcode, item_barcode,
            )
            return False

        borrowed_at = next(
            (i.borrowed_at for i in self.user_items if i.barcode == item_barcode), min_datetime
        )

        payload: UserInfoPayload = {
            "name": self.current_user_name,
            "user_id": user_barcode,
            "email": self.current_user_email,
            "item_id": item_id,
            "borrowed_date": borrowed_at,
            "returned_date": min_datetime,
            "item_status": Status.MISSING,
        }
        success = await backend_checkout(payload)

        if success:
            logger.info(
                "Marked missing: user=%s, item=%s (%s)", user_barcode, item_barcode, item_name
            )
        else:
            logger.error(
                "Mark-missing failed to send: user=%s, item=%s (%s)",
                user_barcode, item_barcode, item_name,
            )
        return success
