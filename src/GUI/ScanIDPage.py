import customtkinter as ctk
from PIL import Image

from GUI import gui_constants as const

# =====================================================
# PAGE 1: SCAN ID
# =====================================================

class ScanIDPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        self.configure(fg_color=const.BG_LIGHT_BLUE)

        # Central container card for clean Olin branding presentation
        card = ctk.CTkFrame(
            self,
            corner_radius=24,
            border_width=2,
            border_color=const.BORDER_BLUE,
            fg_color=const.BG_WHITE
        )
        card.place(relx=0.5, rely=0.5, relwidth=0.88, relheight=0.82, anchor="center")

        # Loaded via a path built from this file's location, so the app
        # doesn't care what directory it was launched from.
        try:
            image_path = const.STATIC_DIR / "green_corner.png"
            img = Image.open(image_path)
            self.corner_tl = ctk.CTkImage(light_image=img,                          dark_image=img,                          size=(90, 90))
            self.corner_tr = ctk.CTkImage(light_image=img.rotate(270, expand=True), dark_image=img.rotate(270, expand=True), size=(90, 90))
            self.corner_bl = ctk.CTkImage(light_image=img.rotate(90,  expand=True), dark_image=img.rotate(90,  expand=True), size=(90, 90))
            self.corner_br = ctk.CTkImage(light_image=img.rotate(180, expand=True), dark_image=img.rotate(180, expand=True), size=(80, 80))

            ctk.CTkLabel(card, image=self.corner_tl, text="").place(relx=.15, rely=.2, anchor="center")
            ctk.CTkLabel(card, image=self.corner_tr, text="").place(relx=.85, rely=.2, anchor="center")
            ctk.CTkLabel(card, image=self.corner_bl, text="").place(relx=.15, rely=.8, anchor="center")
            ctk.CTkLabel(card, image=self.corner_br, text="").place(relx=.85, rely=.8, anchor="center")
        except Exception:
            pass

        ctk.CTkLabel(
            card,
            text="SCAN ID",
            font=const.FONT_HUGE,
            text_color=const.OLIN_BLUE
        ).place(relx=0.5, rely=0.5, anchor="center")
