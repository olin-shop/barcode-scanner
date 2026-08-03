"""
Page asking the user to confirm returning a borrowed item.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import customtkinter as ctk

from GUI.BorrowPage import ConfirmActionPage
from GUI.popup import show_popup

if TYPE_CHECKING:
    from GUI.app import App

# --- Logger Setup ---
logger = logging.getLogger(__name__)


# --- Confirm Return Page ---
class ConfirmReturnPage(ConfirmActionPage):
    """
    Page asking the user to confirm returning a borrowed item. Inherits card layout from ConfirmActionPage.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame) -> None:
        super().__init__(master, title_text="Return Item?")

    def _on_confirm(self) -> None:
        """Initiates async checkout request to confirm item return."""
        app = self.winfo_toplevel()
        app.show_frame("LoadingPage")
        app.run_async(
            app.session.confirm_return(self._item_barcode, self._item_name),
            self._on_return_confirmed,
        )

    def _on_return_confirmed(self, success: bool) -> None:
        """Handles response from backend checkout request."""
        app = self.winfo_toplevel()
        if success:
            app.frames["BorrowedItemsPage"].remove_item(self._item_name)
            app.start_final_confirmation()
        else:
            logger.error(
                "Return could not be confirmed for item=%s (%s); returning to item list.",
                self._item_barcode,
                self._item_name,
            )
            show_popup(
                f"Warning: Could not confirm return for '{self._item_name}'.", self
            )
            app.frames["BorrowedItemsPage"].load(app.session.user_items)
            app.show_frame("BorrowedItemsPage")
