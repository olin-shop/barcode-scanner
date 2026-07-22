from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import customtkinter as ctk

from GUI import gui_constants as const
from GUI.popup import show_popup
from backend.backend_types import BorrowedItem

if TYPE_CHECKING:
    from GUI.GUImain import App

logger = logging.getLogger(__name__)

# =====================================================
# PAGE 2: BORROWED ITEMS
# =====================================================

class BorrowedItemsPage(ctk.CTkFrame):
    """
    Page displaying the list of items currently borrowed by the user.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame) -> None:
        super().__init__(master)

        self.configure(fg_color=const.BG_LIGHT_BLUE)

        ctk.CTkLabel(
            self,
            text="Current Borrowed Items",
            font=const.FONT_TITLE,
            text_color=const.DARK_BLUE_TEXT
        ).pack(pady=20)

        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            width=400,
            height=300,
            fg_color=const.BG_WHITE,
            border_color=const.BORDER_BLUE,
            border_width=2,
            corner_radius=16
        )
        self.scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        ctk.CTkLabel(
            self,
            text="Scan an item to borrow or return",
            font=const.FONT_SUBTITLE,
            text_color=const.MUTED_BLUE_TEXT
        ).pack(side="bottom", pady=20)

        # Internal state: maps item_name -> item_barcode for the current session
        self._item_barcodes: dict[str, str] = {}

    def load(self, items: list[BorrowedItem]) -> None:
        """
        Populate the list from a fresh list of borrowed items.
        Call this every time the page is about to be shown.
        """
        self._item_barcodes = {item.name: item.barcode for item in items}
        self._render(items)

    def remove_item(self, item_name: str) -> None:
        """
        Refresh the displayed list after an item has already been removed
        from the session (return confirmed / marked missing). The session
        is the source of truth here — this just re-renders to match it.
        """
        self._item_barcodes.pop(item_name, None)
        master: App = self.master
        self._render(master.session.user_items)

    def _render(self, items: list[BorrowedItem]) -> None:
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        for item in items:
            date_str = item.borrowed_at.strftime("%b %d, %Y  %H:%M")

            row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            row.pack(fill="x", pady=4, padx=10)

            ctk.CTkButton(
                row,
                text=f"• {item.name}",
                font=const.FONT_ITEM_ROW,
                anchor="w",
                fg_color="transparent",
                text_color=const.DARK_BLUE_TEXT,
                hover_color=const.OLIN_LIGHT_BLUE_HOVER,
                command=lambda n=item.name, bc=item.barcode: self._show_missing_popup(n, bc)
            ).pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                row,
                text=date_str,
                font=const.FONT_DATE,
                text_color=const.MUTED_BLUE_TEXT,
                anchor="e"
            ).pack(side="right", padx=(10, 0))

    def _show_missing_popup(self, item_name: str, item_barcode: str) -> None:
        master: App = self.master
        popup = ctk.CTkToplevel(self)
        popup.title("Mark as Missing")
        popup.overrideredirect(True)
        popup.update_idletasks()
        x = master.winfo_x() + (master.winfo_width()  // 2) - 150
        y = master.winfo_y() + (master.winfo_height() // 2) - 65
        popup.geometry(f"300x130+{x}+{y}")
        popup.grab_set()

        ctk.CTkLabel(
            popup,
            text=f"Mark '{item_name}' as missing?",
            font=const.FONT_POPUP,
            wraplength=260
        ).pack(pady=20)

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack()

        ctk.CTkButton(
            btn_frame,
            text="Mark Missing",
            fg_color=const.MISSING_RED,
            hover_color=const.MISSING_RED_HOVER,
            command=lambda: self._confirm_missing(item_name, item_barcode, popup)
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=popup.destroy
        ).pack(side="right", padx=10)

    def _confirm_missing(self, item_name: str, item_barcode: str, popup) -> None:
        master: App = self.master
        popup.destroy()
        master.show_frame("LoadingPage")
        master.run_async(
            master.session.mark_missing(item_barcode, item_name),
            lambda success: self._on_missing_confirmed(success, item_name, item_barcode),
        )

    def _on_missing_confirmed(self, success: bool, item_name: str, item_barcode: str) -> None:
        master: App = self.master
        if success:
            self.remove_item(item_name)
        else:
            logger.error(
                "Mark-missing could not be confirmed for item=%s (%s).", item_barcode, item_name
            )
            # popup
            show_popup(f"Warning: Could not mark '{item_name}' as missing.", self)
            self._render(master.session.user_items)
        # Stay on BorrowedItemsPage - reset the session timer
        master.show_frame("BorrowedItemsPage")
