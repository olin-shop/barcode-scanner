"""
Starting home page component.
Prompts the user to touch the screen or scan an ID to start a borrowing session.
"""

import customtkinter as ctk
from PIL import Image

from GUI import gui_constants as const


# --- Home Page Component ---
class HomePage(ctk.CTkFrame):
    """
    Landing page presented when the kiosk is idle.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame) -> None:
        super().__init__(master)

        # Base frame background color
        self.configure(fg_color=const.BG_LIGHT_BLUE)

        # Central white card container
        card = ctk.CTkFrame(
            self,
            corner_radius=24,
            border_width=2,
            border_color=const.BORDER_BLUE,
            fg_color=const.BG_WHITE
        )
        card.place(relx=0.5, rely=0.5, relwidth=0.88, relheight=0.82, anchor="center")

        # Top-left logo image
        try:
            logo_path = const.STATIC_DIR / "Olin_Shop_Logo.png"
            if logo_path.exists():
                logo_img = Image.open(logo_path)
                self.logo_image = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(160, 60))
                ctk.CTkLabel(card, image=self.logo_image, text="").place(relx=0.045, rely=0.05, anchor="nw")
        except Exception:
            self.logo_image = None

        # Main welcome header
        ctk.CTkLabel(
            card,
            text="Want to Borrow an Item?",
            font=const.FONT_HEADING,
            text_color=const.DARK_BLUE_TEXT
        ).place(relx=0.5, rely=0.45, anchor="center")

        # Subtitle instruction
        ctk.CTkLabel(
            card,
            text="Tap to Start",
            font=const.FONT_CLOSING_SESSION,
            text_color=const.MUTED_BLUE_TEXT
        ).place(relx=0.5, rely=0.68, anchor="center")

