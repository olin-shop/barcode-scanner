import customtkinter as ctk

from GUI import gui_constants as const

# =====================================================
# PAGE 6: SESSION TIMEOUT
# =====================================================

class SessionTimeoutPage(ctk.CTkFrame):

    def __init__(self, master):
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

        ctk.CTkLabel(
            card,
            text="Session Timed Out",
            font=const.FONT_TIMEOUT_TITLE,
            text_color=const.DARK_BLUE_TEXT
        ).place(relx=0.5, rely=0.42, anchor="center")

        ctk.CTkLabel(
            card,
            text="Returning to start screen..",
            font=const.FONT_TIMEOUT_SUBTITLE,
            text_color=const.MUTED_BLUE_TEXT
        ).place(relx=0.5, rely=0.62, anchor="center")
