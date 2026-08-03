"""
Invalid Item ID Page component.
Displayed when a scanned item barcode is not recognized in the database.
"""

import customtkinter as ctk
from PIL import Image

from GUI import gui_constants as const


# --- Base Invalid Card Page ---
class InvalidCardPage(ctk.CTkFrame):
    """
    Base message card frame displaying logo, heading, subtitle, and responsive window scaling.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame, title_text: str) -> None:
        super().__init__(master)

        # Base frame background styling
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

        # Top-left Olin Shop Logo display
        try:
            logo_path = const.STATIC_DIR / "Olin_Shop_Logo.png"
            if logo_path.exists():
                logo_img = Image.open(logo_path)
                self.logo_image = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(160, 60))
                ctk.CTkLabel(card, image=self.logo_image, text="").place(relx=0.045, rely=0.05, anchor="nw")
        except (OSError, ValueError, AttributeError):
            self.logo_image = None

        # Main alert title header
        self.header_label = ctk.CTkLabel(
            card,
            text=title_text,
            font=const.FONT_CONFIRM_HUGE,
            text_color=const.OLIN_BLUE,
            justify="center"
        )
        self.header_label.place(relx=0.5, rely=0.42, anchor="center")

        # Subtitle instruction label
        self.sub_label = ctk.CTkLabel(
            card,
            text="Please try again",
            font=const.FONT_SUBTITLE,
            text_color=const.MUTED_BLUE_TEXT
        )
        self.sub_label.place(relx=0.5, rely=0.72, anchor="center")

    def update_scale(self, scale: float) -> None:
        """
        Dynamically resizes header text, subtitle text, and logo on window resize.
        """
        new_header_size = max(24, int(80 * scale))
        new_sub_size = max(12, int(28 * scale))
        self.header_label.configure(font=(const.FONT_FAMILY, new_header_size, "bold"))
        self.sub_label.configure(font=(const.FONT_FAMILY, new_sub_size, "bold"))
        if hasattr(self, "logo_image") and self.logo_image:
            w = max(60, int(160 * scale))
            h = max(22, int(60 * scale))
            self.logo_image.configure(size=(w, h))


# --- Invalid Item ID Page ---
class InvalidItemIDPage(InvalidCardPage):
    """
    Page displayed when an item ID barcode is not recognized.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame) -> None:
        super().__init__(master, title_text="Item ID\nNot Recognized")


# Backwards compatibility alias
InvalidItemPage = InvalidItemIDPage
