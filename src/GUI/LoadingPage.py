import customtkinter as ctk

from GUI import gui_constants as const

# =====================================================
# PAGE: Loading in-between screens
# =====================================================

class LoadingPage(ctk.CTkFrame):

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

        self.label = ctk.CTkLabel(
            card,
            text="Loading...",
            font=const.FONT_LOADING,
            text_color=const.OLIN_BLUE
        )
        self.label.place(relx=0.5, rely=0.5, anchor="center")

        self._dots = 3
        self._animate()

    def _animate(self) -> None:
        """Smooth animated movement for loading indicator."""
        try:
            dots_str = "." * self._dots
            self.label.configure(text=f"Loading{dots_str}")
            self._dots = (self._dots % 3) + 1
            self.after(400, self._animate)
        except Exception:
            pass
