from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import customtkinter as ctk

from GUI import gui_constants as const
from GUI.popup import show_popup

if TYPE_CHECKING:
    from GUI.GUImain import App

logger = logging.getLogger(__name__)

# =====================================================
# PAGE 3: CONFIRM BORROW
# =====================================================

class ConfirmBorrowPage(ctk.CTkFrame):
    """
    Page asking the user to confirm borrowing an item.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame) -> None:
        super().__init__(master)

        self.configure(fg_color=const.BG_LIGHT_BLUE)

        card = ctk.CTkFrame(
            self,
            corner_radius=20,
            border_width=2,
            border_color=const.BORDER_BLUE,
            fg_color=const.BG_WHITE
        )
        card.place(relx=0.5, rely=0.5, relwidth=0.88, relheight=0.82, anchor="center")

        ctk.CTkLabel(
            card,
            text="Borrow Item?",
            font=const.FONT_HEADING,
            text_color=const.DARK_BLUE_TEXT
        ).pack(pady=(35, 15))

        self.item_label = ctk.CTkLabel(card, text="", font=const.FONT_BODY, text_color=const.OLIN_BLUE)
        self.item_label.pack(pady=15)

        button_frame = ctk.CTkFrame(card, fg_color="transparent")
        button_frame.pack(pady=35)

        ctk.CTkButton(
            button_frame,
            fg_color=const.CONFIRM_BLUE,
            hover_color=const.CONFIRM_BLUE_HOVER,
            text="Confirm",
            font=const.FONT_BUTTON,
            width=180,
            height=60,
            corner_radius=12,
            command=self._on_confirm
        ).pack(side="left", padx=20)

        ctk.CTkButton(
            button_frame,
            fg_color=const.CANCEL_RED,
            hover_color=const.CANCEL_RED_HOVER,
            text="Cancel",
            font=const.FONT_BUTTON,
            width=180,
            height=60,
            corner_radius=12,
            command=self._on_cancel
        ).pack(side="left", padx=20)

        self._item_name: str = ""
        self._item_barcode: str = ""

    def load(self, item_name: str, item_barcode: str) -> None:
        """Set the item details before showing this page."""
        self._item_name = item_name
        self._item_barcode = item_barcode
        self.item_label.configure(text=item_name)

    def _on_confirm(self) -> None:
        master: App = self.master
        master.show_frame("LoadingPage")
        master.run_async(
            master.session.confirm_borrow(self._item_barcode, self._item_name),
            self._on_borrow_confirmed,
        )

    def _on_borrow_confirmed(self, success: bool) -> None:
        master: App = self.master
        if success:
            master.start_final_confirmation()
        else:
            logger.error(
                "Borrow could not be confirmed for item=%s (%s); returning to item list.",
                self._item_barcode, self._item_name,
            )
            # popup
            show_popup(f"Warning: Could not confirm borrow for '{self._item_name}'.", self)
            master.frames["BorrowedItemsPage"].load(master.session.user_items)
            master.show_frame("BorrowedItemsPage")

    def _on_cancel(self) -> None:
        self.master.show_frame("BorrowedItemsPage")
