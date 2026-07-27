import customtkinter as ctk

from GUI import gui_constants as const

from PIL import Image

# =====================================================
# INVALID USER ID PAGE  
# =====================================================

class InvalidUserPage(ctk.CTkFrame):
    """
    Invalid user ID page.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame) -> None:
        super().__init__(master)

        self.configure(fg_color=const.BG_LIGHT_BLUE)

        card = ctk.CTkFrame(
            self,
            corner_radius=24,
            border_width=2,
            border_color=const.BORDER_BLUE,
            fg_color=const.BG_WHITE
        )
        card.place(relx=0.5, rely=0.5, relwidth=0.88, relheight=0.82, anchor="center")

        # Top-left Olin Shop Logo
        try:
            logo_path = const.STATIC_DIR / "Olin_Shop_Logo.png"
            if logo_path.exists():
                logo_img = Image.open(logo_path)
                self.logo_image = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(160, 60))
                ctk.CTkLabel(card, image=self.logo_image, text="").place(relx=0.045, rely=0.05, anchor="nw")
        except Exception:
            pass

        ctk.CTkLabel(
            card,
            text="User ID Not Recognized",
            font=const.FONT_CONFIRM_HUGE,
            text_color=const.OLIN_BLUE
        ).place(relx=0.5, rely=0.45, anchor="center")

        ctk.CTkLabel(
            card,
            text="Please try again",
            font=const.FONT_CLOSING_SESSION,
            text_color=const.MUTED_BLUE_TEXT
        ).place(relx=0.5, rely=0.68, anchor="center")