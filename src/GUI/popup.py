"""
Popup helper window component for displaying warnings and alert messages.
"""

from typing import Optional
import customtkinter as ctk

from GUI import gui_constants as const


def show_popup(text: str, parent: Optional[ctk.CTk | ctk.CTkFrame] = None) -> ctk.CTkToplevel:
    """
    Displays a centered, frameless popup window with rounded corners containing
    the input text argument and a 'Close' button bottom-center.

    Parameters
    ----------
    text : str
        The message text to display inside the popup.
    parent : ctk.CTk | ctk.CTkFrame, optional
        The parent window or frame to center the popup over. If omitted,
        the root/active window will be resolved automatically.
    """
    if parent is None:
        master = ctk._default_root_mode
    elif hasattr(parent, "winfo_toplevel"):
        master = parent.winfo_toplevel()
    else:
        master = parent

    if master is not None:
        master.update_idletasks()

    popup = ctk.CTkToplevel(master)
    popup.overrideredirect(True)
    popup.attributes("-topmost", True)
    popup.grab_set()

    # Outer container frame for rounded corners and border styling
    container = ctk.CTkFrame(
        popup,
        corner_radius=16,
        border_width=2,
        border_color=const.BORDER_BLUE,
        fg_color=const.BG_WHITE
    )
    container.pack(fill="both", expand=True, padx=2, pady=2)

    # Message text label
    label = ctk.CTkLabel(
        container,
        text=text,
        font=const.FONT_POPUP,
        text_color=const.DARK_BLUE_TEXT,
        wraplength=280,
        justify="center"
    )
    label.pack(pady=(20, 15), padx=20, expand=True)

    # Close button bottom-center
    close_btn = ctk.CTkButton(
        container,
        text="Close",
        font=(const.FONT_FAMILY, 16, "bold"),
        width=110,
        height=36,
        corner_radius=10,
        fg_color=const.OLIN_BLUE,
        hover_color=const.OLIN_BLUE_HOVER,
        command=popup.destroy
    )
    close_btn.pack(side="bottom", pady=(0, 15), anchor="center")

    # Center the popup window relative to master
    popup.update_idletasks()
    width = max(320, container.winfo_reqwidth() + 20)
    height = max(160, container.winfo_reqheight() + 10)

    if master is not None:
        root_x = master.winfo_x()
        root_y = master.winfo_y()
        root_w = master.winfo_width()
        root_h = master.winfo_height()

        x = root_x + (root_w // 2) - (width // 2)
        y = root_y + (root_h // 2) - (height // 2)
    else:
        x = 200
        y = 200

    popup.geometry(f"{width}x{height}+{x}+{y}")

    return popup
