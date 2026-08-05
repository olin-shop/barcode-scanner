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
        self.card = ctk.CTkFrame(
            self,
            corner_radius=24,
            border_width=2,
            border_color=const.BORDER_BLUE,
            fg_color=const.BG_WHITE,
        )
        self.card.place(relx=0.5, rely=0.5, relwidth=0.88, relheight=0.82, anchor="center")

        # Top-left logo image
        self.logo_label = None
        try:
            logo_path = const.STATIC_DIR / "Olin_Shop_Logo.png"
            if logo_path.exists():
                logo_img = Image.open(logo_path)
                self.logo_image = ctk.CTkImage(
                    light_image=logo_img, dark_image=logo_img, size=(160, 60)
                )
                self.logo_label = ctk.CTkLabel(self.card, image=self.logo_image, text="")
                self.logo_label.place(relx=0.045, rely=0.05, anchor="nw")
        except (OSError, ValueError, AttributeError):
            self.logo_image = None

        # Main welcome header
        self.header_label = ctk.CTkLabel(
            self.card,
            text="Want to Borrow an Item?",
            font=const.FONT_HEADING_HUGE,
            text_color=const.OLIN_BLUE
        )
        self.header_label.place(relx=0.5, rely=0.45, anchor="center")

        # Subtitle instruction
        self.subtitle_label = ctk.CTkLabel(
            self.card,
            text="Tap to Start",
            font=const.FONT_BODY,
            text_color=const.MUTED_BLUE_TEXT
        )
        self.subtitle_label.place(relx=0.5, rely=0.68, anchor="center")

        # Bind tap/click events to navigate to SelectUserPage across all background and label elements
        self._bind_tap_recursively(self, self._on_tap)

    def _bind_tap_recursively(self, widget, callback) -> None:
        """Recursively binds tap events to widget, canvas, canvas items, and label."""
        for evt in ("<Button-1>", "<ButtonPress-1>", "<ButtonRelease-1>"):
            try:
                widget.bind(evt, callback)
            except Exception:
                pass
            if hasattr(widget, "_canvas") and widget._canvas:
                try:
                    widget._canvas.bind(evt, callback)
                    widget._canvas.tag_bind("all", evt, callback)
                except Exception:
                    pass
            if hasattr(widget, "_label") and widget._label:
                try:
                    widget._label.bind(evt, callback)
                except Exception:
                    pass
        for child in widget.winfo_children():
            self._bind_tap_recursively(child, callback)



    def _on_tap(self, event=None) -> None:
        """Navigates to SelectUserPage when screen is tapped."""
        app = self.winfo_toplevel()
        if hasattr(app, "show_frame"):
            app.show_frame("SelectUserPage")


