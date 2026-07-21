import customtkinter as ctk

from GUI.GUImain import backend_confirm_return
from GUI.GUImain import App
# =====================================================
# PAGE 4: CONFIRM RETURN
# =====================================================

class ConfirmReturnPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        self.confirm_button = ctk.CTkButton(
            self, 
            text="Confirm Borrow", 
            command=lambda: self.master.execute_transaction(self.item_barcode, "")
        )

        ctk.CTkLabel(
            self,
            text="Return Item?",
            font=("Arial", 36, "bold")
        ).pack(pady=30)

        self.item_label = ctk.CTkLabel(self, text="", font=("Arial", 28))
        self.item_label.pack(pady=20)

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=40)

        ctk.CTkButton(
            button_frame,
            fg_color="#19ca63",
            hover_color="#219250",
            text="Confirm",
            font=("Arial", 30),
            width=180,
            height=60,
            command=self._on_confirm
        ).pack(side="left", padx=20)

        ctk.CTkButton(
            button_frame,
            fg_color="#cd2828",
            hover_color="#922121",
            text="Cancel",
            font=("Arial", 30),
            width=180,
            height=60,
            command=self._on_cancel
        ).pack(side="left", padx=20)

        self._item_name    = ""
        self._item_barcode = ""

    def load(self, item_name: str, item_barcode: str) -> None:
        """Set the item details before showing this page."""
        self._item_name    = item_name
        self._item_barcode = item_barcode
        self.item_label.configure(text=item_name)

    def _on_confirm(self) -> None:
        master: App = self.master
        backend_confirm_return(master.current_user_barcode, self._item_barcode, self._item_name)
        self.master.frames["BorrowedItemsPage"].remove_item(self._item_name)
        master.start_final_confirmation()

    def _on_cancel(self) -> None:
        self.master.show_frame("BorrowedItemsPage")
