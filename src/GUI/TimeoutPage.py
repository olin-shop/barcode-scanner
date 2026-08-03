"""
Session Timeout page.
"""

import customtkinter as ctk
from PIL import Image

from GUI import gui_constants as const


class SessionTimeoutPage(ctk.CTkFrame):
    """
    Timeout page shown when the user is inactive for too long.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame) -> None:
        super().__init__(master)

        self.configure(fg_color=const.BG_LIGHT_BLUE)

        card = ctk.CTkFrame(
            self,
            corner_radius=24,
            border_width=2,
            border_color=const.BORDER_BLUE,
            fg_color=const.BG_WHITE,
        )
        card.place(relx=0.5, rely=0.5, relwidth=0.88, relheight=0.82, anchor="center")

        ctk.CTkLabel(
            card,
            text="Session Timed Out",
            font=const.FONT_TIMEOUT_TITLE,
            text_color=const.DARK_BLUE_TEXT,
        ).place(relx=0.5, rely=0.42, anchor="center")

        ctk.CTkLabel(
            card,
            text="Returning to start screen..",
            font=const.FONT_TIMEOUT_SUBTITLE,
            text_color=const.MUTED_BLUE_TEXT,
        ).place(relx=0.5, rely=0.62, anchor="center")

        # Top-left Olin Shop Logo
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
        except Exception:
            pass
