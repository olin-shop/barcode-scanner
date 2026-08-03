"""
Page asking the user to confirm borrowing an item.
"""

import logging
import customtkinter as ctk
from PIL import Image

from GUI import gui_constants as const
from GUI.popup import show_popup

# --- Logger Setup ---
logger = logging.getLogger(__name__)


# --- Base Action Confirmation Page ---
class ConfirmActionPage(ctk.CTkFrame):
    """
    Base frame providing card layout, heading, item name display, and Confirm/Cancel action buttons.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame, title_text: str) -> None:
        super().__init__(master)

        # Base frame background setup
        self.configure(fg_color=const.BG_LIGHT_BLUE)

        # Central white card container
        card = ctk.CTkFrame(
            self,
            corner_radius=20,
            border_width=2,
            border_color=const.BORDER_BLUE,
            fg_color=const.BG_WHITE,
        )
        card.place(relx=0.5, rely=0.5, relwidth=0.88, relheight=0.82, anchor="center")

        # Action title header
        ctk.CTkLabel(
            card,
            text=title_text,
            font=const.FONT_HEADING_HUGE,
            text_color=const.DARK_BLUE_TEXT
        ).pack(pady=(60, 15))

        # Dynamic item name label
        self.item_label = ctk.CTkLabel(
            card, text="", font=const.FONT_BODY, text_color=const.OLIN_BLUE
        )
        self.item_label.pack(pady=15)

        # Top-left logo image
        try:
            logo_path = const.STATIC_DIR / "Olin_Shop_Logo.png"
            if logo_path.exists():
                logo_img = Image.open(logo_path)
                self.logo_image = ctk.CTkImage(
                    light_image=logo_img, dark_image=logo_img, size=(160, 60)
                )
                ctk.CTkLabel(card, image=self.logo_image, text="").place(
                    relx=0.045, rely=0.05, anchor="nw"
                )
        except (OSError, ValueError, AttributeError):
            self.logo_image = None

        # Container for action buttons
        button_frame = ctk.CTkFrame(card, fg_color="transparent")
        button_frame.pack(pady=(25, 20))

        # Confirm button
        ctk.CTkButton(
            button_frame,
            fg_color=const.CONFIRM_BLUE,
            hover_color=const.CONFIRM_BLUE_HOVER,
            text="CONFIRM",
            font=const.FONT_BUTTON,
            width=210,
            height=70,
            corner_radius=34,
            command=self._on_confirm
        ).pack(side="left", padx=20)

        # Cancel button
        ctk.CTkButton(
            button_frame,
            fg_color=const.OLIN_PINK,
            hover_color=const.CANCEL_RED_HOVER,
            text="CANCEL",
            font=const.FONT_BUTTON,
            width=210,
            height=70,
            corner_radius=34,
            command=self._on_cancel
        ).pack(side="left", padx=20)

        self._item_name: str = ""
        self._item_barcode: str = ""

    def load(self, item_name: str, item_barcode: str) -> None:
        """
        Sets the item name and barcode before displaying the confirmation page.
        """
        self._item_name = item_name
        self._item_barcode = item_barcode
        self.item_label.configure(text=item_name)

    def _on_confirm(self) -> None:
        """Subclasses override this method to handle confirmation."""
        pass

    def _on_cancel(self) -> None:
        """Handles Cancel button click to navigate back to BorrowedItemsPage."""
        app = self.winfo_toplevel()
        app.show_frame("BorrowedItemsPage")


# --- Confirm Borrow Page ---
class ConfirmBorrowPage(ConfirmActionPage):
    """
    Page asking the user to confirm borrowing a scanned item.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame) -> None:
        super().__init__(master, title_text="Borrow Item?")

    def _on_confirm(self) -> None:
        """Initiates async checkout request to confirm borrow."""
        app = self.winfo_toplevel()
        app.show_frame("LoadingPage")
        app.run_async(
            app.session.confirm_borrow(self._item_barcode, self._item_name),
            self._on_borrow_confirmed,
        )

    def _on_borrow_confirmed(self, success: bool) -> None:
        """Handles response from backend checkout request."""
        app = self.winfo_toplevel()
        if success:
            app.start_final_confirmation()
        else:
            logger.error(
                "Borrow could not be confirmed for item=%s (%s); returning to item list.",
                self._item_barcode,
                self._item_name,
            )
            show_popup(
                f"Warning: Could not confirm borrow for '{self._item_name}'.", self
            )
            app.frames["BorrowedItemsPage"].load(app.session.user_items)
            app.show_frame("BorrowedItemsPage")
