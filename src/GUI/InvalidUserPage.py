"""
Invalid User ID Page component.
Displayed when a scanned user ID barcode is not recognized in the database.
"""

import customtkinter as ctk
from GUI.InvalidItemPage import InvalidCardPage


# --- Invalid User Page Component ---
class InvalidUserPage(InvalidCardPage):
    """
    Page displayed when a user ID is not recognized. Inherits card layout and scaling from InvalidCardPage.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame) -> None:
        super().__init__(master, title_text="User ID\nNot Recognized")