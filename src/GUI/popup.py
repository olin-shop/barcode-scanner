"""
Popup helper window component for displaying warnings and alert messages.
"""

from typing import Optional, Callable
import customtkinter as ctk

from GUI import gui_constants as const


# --- Shared Popup Helper ---
def _create_popup_base(
    text: str, min_width: int, parent: Optional[ctk.CTk | ctk.CTkFrame] = None
) -> tuple[ctk.CTkToplevel, ctk.CTkFrame]:
    """
    Creates and positions a centered, frameless top-level popup window.
    """
    # Resolve parent window instance
    if parent is None:
        master = None
    elif hasattr(parent, "winfo_toplevel"):
        master = parent.winfo_toplevel()
    else:
        master = parent

    if master is not None:
        master.update_idletasks()

    # Create top-level window configuration
    popup = ctk.CTkToplevel(master)
    popup.withdraw()
    popup.overrideredirect(True)
    popup.attributes("-topmost", True)
    popup.configure(fg_color=const.BG_WHITE)

    # Outer container frame with border styling
    container = ctk.CTkFrame(
        popup,
        corner_radius=16,
        border_width=2,
        border_color=const.BORDER_BLUE,
        fg_color=const.BG_WHITE,
    )
    container.pack(fill="both", expand=True)

    # Message text display label
    label = ctk.CTkLabel(
        container,
        text=text,
        font=const.FONT_POPUP,
        text_color=const.DARK_BLUE_TEXT,
        wraplength=280,
        justify="center",
    )
    label.pack(pady=(20, 15), padx=20, expand=True)

    # Calculate centered screen coordinates relative to master
    popup.update_idletasks()
    width = max(min_width, container.winfo_reqwidth() + 20)
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
    popup.deiconify()
    popup.update()

    def safe_grab():
        if popup.winfo_exists():
            try:
                popup.grab_set()
            except Exception:
                pass

    popup.after(10, safe_grab)
    return popup, container


# --- Single Action Alert Popup ---
def show_popup(
    text: str, parent: Optional[ctk.CTk | ctk.CTkFrame] = None
) -> ctk.CTkToplevel:
    """
    Displays a centered, frameless popup window containing an alert message and a 'Close' button.
    """
    # Create base popup window
    popup, container = _create_popup_base(text, min_width=320, parent=parent)

    # Add single Close button at bottom-center
    close_btn = ctk.CTkButton(
        container,
        text="Close",
        font=(const.FONT_FAMILY, 16, "bold"),
        width=110,
        height=36,
        corner_radius=10,
        fg_color=const.OLIN_BLUE,
        hover_color=const.OLIN_BLUE_HOVER,
        command=popup.destroy,
    )
    close_btn.pack(side="bottom", pady=(0, 15), anchor="center")

    return popup


# --- Two-Choice Confirmation Popup ---
def show_confirm_popup(
    text: str,
    confirm_text: str,
    on_confirm: Callable[[], None],
    parent: Optional[ctk.CTk | ctk.CTkFrame] = None,
    confirm_color: Optional[str] = None,
    confirm_hover_color: Optional[str] = None,
) -> ctk.CTkToplevel:
    """
    Displays a centered popup window with two choices: a confirmation button and a 'Cancel' button.
    """
    # Create base popup window
    popup, container = _create_popup_base(text, min_width=340, parent=parent)

    # Container frame for action buttons
    btn_frame = ctk.CTkFrame(container, fg_color="transparent")
    btn_frame.pack(side="bottom", pady=(0, 15), anchor="center")

    def handle_confirm():
        popup.destroy()
        on_confirm()

    # Confirm action button
    confirm_btn = ctk.CTkButton(
        btn_frame,
        text=confirm_text,
        font=(const.FONT_FAMILY, 16, "bold"),
        width=130,
        height=36,
        corner_radius=10,
        fg_color=confirm_color or const.OLIN_PINK,
        hover_color=confirm_hover_color or const.MISSING_RED_HOVER,
        command=handle_confirm,
    )
    confirm_btn.pack(side="left", padx=8)

    # Cancel action button
    cancel_btn = ctk.CTkButton(
        btn_frame,
        text="Cancel",
        font=(const.FONT_FAMILY, 16, "bold"),
        width=110,
        height=36,
        corner_radius=10,
        fg_color=const.OLIN_BLUE,
        hover_color=const.OLIN_BLUE_HOVER,
        command=popup.destroy,
    )
    cancel_btn.pack(side="left", padx=8)

    return popup
