from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

import customtkinter as ctk

from GUI import gui_constants as const
from GUI.popup import show_popup, show_confirm_popup
from backend.backend_types import BorrowedItem

if TYPE_CHECKING:
    from GUI.GUImain import App

logger = logging.getLogger(__name__)

# =====================================================
# BORROWED ITEMS PAGE
# =====================================================

class BorrowedItemsPage(ctk.CTkFrame):
    """
    Page displaying the list of items currently borrowed by the user.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame) -> None:
        super().__init__(master)

        self.configure(fg_color=const.BG_LIGHT_BLUE)

        # Header banner canvas extending 80% across with a 70-degree forward-slash right edge
        banner_height = 75
        self.banner_canvas = ctk.CTkCanvas(
            self,
            bg=const.BG_LIGHT_BLUE,
            highlightthickness=0,
            bd=0
        )
        self.banner_canvas.place(x=0, y=0, relwidth=1.0, height=banner_height)

        def _draw_banner(event=None) -> None:
            self.banner_canvas.delete("all")
            w = self.banner_canvas.winfo_width()
            h = self.banner_canvas.winfo_height()
            if w <= 1 or h <= 1:
                return

            # 1. Slanted banner polygon
            top_right = w * 0.70
            dx = h / math.tan(math.radians(70))
            bot_right = top_right - dx
            points = [0, 10, top_right, 10, bot_right, h, 0, h]
            self.banner_canvas.create_polygon(points, fill=const.OLIN_BLUE_HOVER, outline="")

            # 2. Line of small OLIN_PINK squares drawn directly on canvas (seamless across backgrounds)
            sq_size = 8
            spacing = 8
            y0 = 20
            start_x = w * 0.98
            for i in range(20):
                x1 = start_x - (i * (sq_size + spacing)) - sq_size - 50
                y1 = y0
                x2 = x1 + sq_size
                y2 = y1 + sq_size
                self.banner_canvas.create_rectangle(x1, y1, x2, y2, fill=const.OLIN_PINK, outline="")

        self.banner_canvas.bind("<Configure>", _draw_banner)

        # Header title text rendered over the banner in crisp white
        ctk.CTkLabel(
            self,
            text="Current Borrowed Items",
            font=(const.FONT_FAMILY, 30, "bold"),
            text_color=const.BG_LIGHT_BLUE,
            fg_color=const.OLIN_BLUE_HOVER
        ).place(x=30, y=banner_height / 2, anchor="w")

        # Large User Name label positioned in the extra space below the top banner
        self.user_name_label = ctk.CTkLabel(
            self,
            text="",
            font=(const.FONT_FAMILY, 32, "bold"),
            text_color=const.DARK_BLUE_TEXT,
            anchor="center"
        )
        self.user_name_label.pack(pady=(85, 5), padx=25, anchor="center")

        # Shortened items list frame moved lower down
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            width=400,
            height=160,
            fg_color=const.BG_WHITE,
            border_color=const.BORDER_BLUE,
            border_width=2,
            corner_radius=16
        )
        self.scroll_frame.pack(pady=(5, 10), padx=20, fill="both", expand=True)

        # Hide visual scrollbar bar and rebalance grid padding so content is perfectly centered
        try:
            self.scroll_frame._scrollbar.grid_forget()
            self.scroll_frame._scrollbar.configure(width=0)
            self.scroll_frame._parent_canvas.grid_configure(padx=10)
        except Exception:
            pass

        # Touchscreen swipe / drag scrolling support
        self._swipe_last_y = 0
        self._is_swiping = False

        def _on_swipe_start(e):
            self._is_swiping = True
            self._swipe_last_y = e.y_root

        def _on_swipe_drag(e):
            if not self._is_swiping or self._swipe_last_y == 0:
                return
            dy = self._swipe_last_y - e.y_root
            self._swipe_last_y = e.y_root
            if abs(dy) > 0:
                step = 1 if dy > 0 else -1
                self.scroll_frame._parent_canvas.yview_scroll(step, "units")

        def _on_swipe_end(e):
            self._is_swiping = False

        try:
            canvas = self.scroll_frame._parent_canvas
            canvas.bind("<ButtonPress-1>", _on_swipe_start, add="+")
            canvas.bind("<B1-Motion>", _on_swipe_drag, add="+")
            canvas.bind("<ButtonRelease-1>", _on_swipe_end, add="+")
        except Exception:
            pass

        ctk.CTkLabel(
            self,
            text="Scan an item to borrow or return",
            font=const.FONT_SUBTITLE,
            text_color=const.OLIN_PINK
        ).pack(side="bottom", pady=(5, 30))

        # Home Button in bottom right corner (transparent background, text changes to dark blue on hover)
        self.home_button = ctk.CTkButton(
            self,
            text="HOME",
            font=const.FONT_BUTTON,
            fg_color="transparent",
            hover=False,
            text_color=const.OLIN_BLUE,
            corner_radius=0,
            width=80,
            height=36,
            command=self._on_home_clicked
        )
        self.home_button.place(relx=0.96, rely=0.97, anchor="se")
        self.home_button.bind("<Enter>", lambda e: self.home_button.configure(text_color=const.DARK_BLUE_TEXT))
        self.home_button.bind("<Leave>", lambda e: self.home_button.configure(text_color=const.OLIN_BLUE))

        # Internal state: maps item_name -> item_barcode for the current session
        self._item_barcodes: dict[str, str] = {}

    def _on_home_clicked(self) -> None:
        """Navigates back to HomePage and resets session."""
        app = self.winfo_toplevel()
        if hasattr(app, "reset_session"):
            app.reset_session()
        elif hasattr(app, "show_frame"):
            app.show_frame("HomePage")

    def load(self, items: list[BorrowedItem], user_name: str | None = None) -> None:
        """
        Populate the list from a fresh list of borrowed items and update user display name.
        Call this every time the page is about to be shown.
        """
        self._item_barcodes = {item.name: item.barcode for item in items}

        if not user_name:
            session = getattr(self.master, "session", None)
            if session and getattr(session, "current_user_name", None):
                user_name = session.current_user_name

        display_name = user_name if user_name else ""
        self.user_name_label.configure(text=display_name)

        self._render(items)

    def remove_item(self, item_name: str) -> None:
        """
        Refresh the displayed list after an item has already been removed
        from the session (return confirmed / marked missing). The session
        is the source of truth here — this just re-renders to match it.
        """
        self._item_barcodes.pop(item_name, None)
        master: App = self.master
        session = getattr(master, "session", None)
        items = session.user_items if session else []
        user_name = session.current_user_name if session else None
        self.load(items, user_name=user_name)

    def _render(self, items: list[BorrowedItem]) -> None:
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        for idx, item in enumerate(items):
            date_str = item.borrowed_at.strftime("%b %d, %Y  %H:%M")
            bg_color = const.BG_WHITE if idx % 2 == 0 else const.BG_LIGHT_BLUE

            row = ctk.CTkFrame(
                self.scroll_frame,
                fg_color=bg_color,
                corner_radius=8
            )
            row.pack(fill="x", pady=3, padx=5)

            ctk.CTkButton(
                row,
                text=item.name,
                font=const.FONT_ITEM_ROW,
                anchor="w",
                fg_color="transparent",
                text_color=const.DARK_BLUE_TEXT,
                hover_color=const.OLIN_LIGHT_BLUE_HOVER,
                height=38,
                command=lambda n=item.name, bc=item.barcode: self._show_missing_popup(n, bc)
            ).pack(side="left", fill="x", expand=True, padx=(10, 0))

            ctk.CTkLabel(
                row,
                text=date_str,
                font=const.FONT_DATE,
                text_color=const.MUTED_BLUE_TEXT,
                anchor="e"
            ).pack(side="right", padx=(10, 15))

    def _show_missing_popup(self, item_name: str, item_barcode: str) -> None:
        show_confirm_popup(
            text=f"Mark '{item_name}' as missing?",
            confirm_text="Mark Missing",
            on_confirm=lambda: self._confirm_missing(item_name, item_barcode),
            parent=self
        )

    def _confirm_missing(self, item_name: str, item_barcode: str) -> None:
        app = self.winfo_toplevel()
        app.show_frame("LoadingPage")
        app.run_async(
            app.session.mark_missing(item_barcode, item_name),
            lambda success: self._on_missing_confirmed(success, item_name, item_barcode),
        )

    def _on_missing_confirmed(self, success: bool, item_name: str, item_barcode: str) -> None:
        app = self.winfo_toplevel()
        if success:
            self.remove_item(item_name)
        else:
            logger.error(
                "Mark-missing could not be confirmed for item=%s (%s).", item_barcode, item_name
            )
            # popup
            show_popup(f"Warning: Could not mark '{item_name}' as missing.", self)
            self._render(app.session.user_items)
        # Stay on BorrowedItemsPage - reset the session timer
        app.show_frame("BorrowedItemsPage")

    def update_scale(self, scale: float) -> None:
        """Dynamically scale Home button and layout components on window resize."""
        if hasattr(self, "home_button"):
            self.home_button.configure(
                font=(const.FONT_FAMILY, max(12, int(20 * scale)), "bold"),
                width=max(60, int(110 * scale)),
                height=max(28, int(44 * scale))
            )
