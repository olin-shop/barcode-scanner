import customtkinter as ctk
from datetime import datetime
from GUI.GUImain import App
from GUI.GUImain import backend_mark_missing

from backend.requests import get_item
from backend.backend_types import Status

# =====================================================
# PAGE 2: BORROWED ITEMS
# =====================================================

class BorrowedItemsPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        ctk.CTkLabel(
            self,
            text="Current Borrowed Items",
            font=("Arial", 32, "bold")
        ).pack(pady=20)

        self.scroll_frame = ctk.CTkScrollableFrame(self, width=400, height=300)
        self.scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        ctk.CTkLabel(
            self,
            text="Scan an item to borrow or return",
            font=("Arial", 18)
        ).pack(side="bottom", pady=20)

        # Internal state: maps item_name → item_barcode for the current session
        # (item_name is kept only as an internal key so other pages that still
        # pass names around continue to work; it is never shown in the list)
        self._item_barcodes: dict[str, str] = {}

    def load(self, items: list[tuple[str, str, datetime]]) -> None:
        """
        Populate the list from a fresh (item_name, item_barcode, borrowed_at) list.
        Call this every time the page is about to be shown.
        """
        self._item_barcodes = {name: bc for name, bc, _ in items}
        self._render(items)

    def remove_item(self, item_name: str) -> None:
        """
        Remove one item from the displayed list and internal map.
        Called after a return is confirmed or an item is marked missing.
        """
        self._item_barcodes.pop(item_name, None)
        # Rebuild display from remaining items (no dates needed here, use placeholders)
        # Re-render by asking the master for the current user_items minus this one
        master: App = self.master
        master.user_items = [(n, bc, dt) for n, bc, dt in master.user_items if n != item_name]
        self._render(master.user_items)

    def _render(self, items: list[tuple[str, str, datetime]]) -> None:
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        for item_name, item_barcode, borrowed_at in items:
            date_str = borrowed_at.strftime("%b %d, %Y  %H:%M")

            row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            row.pack(fill="x", pady=4, padx=10)

            ctk.CTkButton(
                row,
                text=f"• {item_barcode}",
                font=("Arial", 24),
                anchor="w",
                fg_color="transparent",
                text_color=("black", "white"),
                hover_color=("gray85", "gray25"),
                command=lambda n=item_name, bc=item_barcode: self._show_missing_popup(n, bc)
            ).pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                row,
                text=date_str,
                font=("Arial", 16),
                text_color=("gray40", "gray70"),
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

        # The row only knows the barcode; the display name is fetched from the
        # backend (get_item) so it can still be shown here.
        message_label = ctk.CTkLabel(
            popup,
            text="Looking up item...",
            font=("Arial", 16),
            wraplength=260
        )
        message_label.pack(pady=20)

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack()

        mark_missing_btn = ctk.CTkButton(
            btn_frame,
            text="Mark Missing",
            fg_color="red",
            hover_color="darkred",
            state="disabled",
            command=lambda: self._confirm_missing(item_name, item_barcode, popup)
        )
        mark_missing_btn.pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=popup.destroy
        ).pack(side="right", padx=10)

        def _on_item_fetched(result: tuple[str, Status]) -> None:
            # Popup may have already been closed (Cancel/Confirm) by the time
            # the backend responds.
            if not popup.winfo_exists():
                return

            fetched_name, _status = result
            display_name = fetched_name or item_name or item_barcode
            message_label.configure(text=f"Mark '{display_name}' as missing?")
            mark_missing_btn.configure(state="normal")

        try:
            barcode_arg = int(item_barcode)
        except ValueError:
            barcode_arg = item_barcode

        master.run_async(get_item(barcode_arg), _on_item_fetched)

    def _confirm_missing(self, item_name: str, item_barcode: str, popup) -> None:
        master: App = self.master
        backend_mark_missing(master.current_user_barcode, item_barcode, item_name)
        popup.destroy()
        self.remove_item(item_name)
        # Stay on BorrowedItemsPage – reset the session timer
        master._reset_timeout_timer("BorrowedItemsPage")