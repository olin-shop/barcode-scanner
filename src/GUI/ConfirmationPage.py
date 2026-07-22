import customtkinter as ctk

from GUI import gui_constants as const

# =====================================================
# PAGE 5: FINAL CONFIRMATION
# =====================================================

class FinalConfirmationPage(ctk.CTkFrame):
    """
    Confirmation page shown briefly before the session is reset.
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

        ctk.CTkLabel(
            card,
            text="Confirmed",
            font=const.FONT_CONFIRM_HUGE,
            text_color=const.OLIN_BLUE
        ).place(relx=0.5, rely=0.45, anchor="center")

        ctk.CTkLabel(
            card,
            text="Closing session..",
            font=const.FONT_CLOSING_SESSION,
            text_color=const.MUTED_BLUE_TEXT
        ).place(relx=0.5, rely=0.68, anchor="center")
