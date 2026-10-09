"""
Standalone GUI Screen Preview Tool.
Allows quick visual testing and navigation between all application pages.
DOES NOT MODIFY ANY EXISTING CODE - SAFE TO RUN AND DELETE BEFORE COMMITTING.
"""

import sys
import os
from pathlib import Path

try:
    import pandas
except ImportError:
    from unittest.mock import MagicMock
    sys.modules["pandas"] = MagicMock()

# Provide mock fallback environment variables if .env is missing key variables
default_env = {
    "NAME_URL": "http://localhost:5000/name",
    "ITEM_URL": "http://localhost:5000/item",
    "CHECKOUT_URL": "http://localhost:5000/checkout",
    "BORROWED_ITEMS_URL": "http://localhost:5000/borrowed-items",
    "INTRO_URL": "http://localhost:5000/intro-sheet",
    "ELEC_URL": "http://localhost:5000/303-sheet",
    "PORT": "5000",
    "HOST_IP": "127.0.0.1",
}
for k, v in default_env.items():
    os.environ.setdefault(k, v)

# Add src to python path for standalone execution
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import customtkinter as ctk

from GUI import gui_constants as const
from GUI.session_manager import SessionManager
from GUI.HomePage import HomePage
from GUI.SelectUserPage import SelectUserPage
from GUI.BorrowedItemsPage import BorrowedItemsPage
from GUI.BorrowPage import ConfirmBorrowPage
from GUI.ReturnPage import ConfirmReturnPage
from GUI.ConfirmationPage import FinalConfirmationPage
from GUI.TimeoutPage import SessionTimeoutPage
from GUI.LoadingPage import LoadingPage
from GUI.InvalidItemPage import InvalidItemIDPage
from backend.backend_types import BorrowedItem
from datetime import datetime


class ScreenViewerApp(ctk.CTk):
    """
    Standalone preview app providing a top control toolbar to preview all GUI screens.
    """

    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("light")
        self.geometry(const.WINDOW_SIZE)
        self.title("GUI Screen Visual Tester")
        self.configure(fg_color=const.BG_LIGHT_BLUE)

        self.session = SessionManager()

        # Top navigation bar for previewing screens
        self.top_bar = ctk.CTkScrollableFrame(
            self,
            orientation="horizontal",
            fg_color="#D8ECF8",
            height=50,
            corner_radius=0
        )
        self.top_bar.pack(side="top", fill="x")

        # Container frame for screen pages
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(side="top", fill="both", expand=True)

        self.frames = {}
        page_classes = [
            HomePage,
            SelectUserPage,
            BorrowedItemsPage,
            ConfirmBorrowPage,
            ConfirmReturnPage,
            FinalConfirmationPage,
            SessionTimeoutPage,
            LoadingPage,
            InvalidItemIDPage,
        ]

        for F in page_classes:
            name = F.__name__
            frame = F(self.container)
            self.frames[name] = frame
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

            # Add toolbar button for each page
            btn = ctk.CTkButton(
                self.top_bar,
                text=name.replace("Page", ""),
                font=("DIN OT", 13, "bold"),
                fg_color=const.CONFIRM_BLUE,
                hover_color=const.CONFIRM_BLUE_HOVER,
                width=110,
                height=32,
                command=lambda n=name: self.switch_screen(n)
            )
            btn.pack(side="left", padx=4, pady=8)

        # Show initial preview screen
        self.switch_screen("HomePage")

    def switch_screen(self, page_name: str) -> None:
        """Switches the active preview frame."""
        frame = self.frames[page_name]

        if page_name == "BorrowedItemsPage":
            frame.load([], user_name="")
        elif page_name == "ConfirmBorrowPage":
            frame.load("", "")
        elif page_name == "ConfirmReturnPage":
            frame.load("", "")
        elif page_name == "SelectUserPage":
            frame.load_students()

        frame.tkraise()

    def show_frame(self, page_name: str) -> None:
        self.switch_screen(page_name)

    def reset_session(self) -> None:
        self.session.reset()
        self.switch_screen("HomePage")


def main() -> None:
    app = ScreenViewerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
