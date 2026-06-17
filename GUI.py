import customtkinter as ctk
from PIL import Image
from datetime import datetime

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# =====================================================
# BACKEND HOOKS
# Replace each function body with your real logic.
# =====================================================

def backend_get_user_items(user_barcode: str) -> list[tuple[str, str, datetime]]:
    """
    Called after a user ID is scanned.

    Args:
        user_barcode: The raw barcode string from the scanner.

    Returns:
        List of (item_name, item_barcode, borrowed_at) tuples for all items
        currently borrowed by this user.
        Return an empty list if the user has no borrowed items.

    Example return value:
        [
            ("Multimeter",     "BC001", datetime(2025, 6, 14,  9, 30)),
            ("Oscilloscope",   "BC002", datetime(2025, 6, 15, 14,  5)),
        ]
    """
    # ── REPLACE WITH REAL LOGIC ──────────────────────────────────────────────
    return [
        ("Multimeter",     "BC001", datetime(2025, 6, 14,  9, 30)),
        ("Oscilloscope",   "BC002", datetime(2025, 6, 15, 14,  5)),
        ("Power Supply",   "BC003", datetime(2025, 6, 16, 11,  0)),
        ("Soldering Iron", "BC004", datetime(2025, 6, 16, 13, 45)),
    ]
    # ─────────────────────────────────────────────────────────────────────────


def backend_lookup_item(item_barcode: str, user_items: list[tuple[str, str, datetime]]) -> tuple[str, bool]:
    """
    Called when an item barcode is scanned on the BorrowedItemsPage.

    Args:
        item_barcode:  The raw barcode string from the scanner.
        user_items:    The current list of (item_name, item_barcode, borrowed_at)
                       tuples for the active user.

    Returns:
        (item_name, is_borrowed) where:
            item_name   – human-readable name for the item
            is_borrowed – True  → item is already borrowed by this user → show ConfirmReturnPage
                          False → item is new                           → show ConfirmBorrowPage
    """
    # ── REPLACE WITH REAL LOGIC ──────────────────────────────────────────────
    for name, bc, _ in user_items:
        if bc == item_barcode:
            return name, True
    return f"Item ({item_barcode})", False
    # ─────────────────────────────────────────────────────────────────────────


def backend_confirm_borrow(user_barcode: str, item_barcode: str, item_name: str) -> None:
    """
    Called when the user confirms borrowing a new item.

    Args:
        user_barcode: Active user's barcode.
        item_barcode: The item being borrowed.
        item_name:    Human-readable item name.
    """
    # ── REPLACE WITH REAL LOGIC ──────────────────────────────────────────────
    print(f"[BACKEND] Borrow confirmed: user={user_barcode}, item={item_barcode} ({item_name})")
    # ─────────────────────────────────────────────────────────────────────────


def backend_confirm_return(user_barcode: str, item_barcode: str, item_name: str) -> None:
    """
    Called when the user confirms returning a borrowed item.

    Args:
        user_barcode: Active user's barcode.
        item_barcode: The item being returned.
        item_name:    Human-readable item name.
    """
    # ── REPLACE WITH REAL LOGIC ──────────────────────────────────────────────
    print(f"[BACKEND] Return confirmed: user={user_barcode}, item={item_barcode} ({item_name})")
    # ─────────────────────────────────────────────────────────────────────────


def backend_mark_missing(user_barcode: str, item_barcode: str, item_name: str) -> None:
    """
    Called when the user marks a borrowed item as missing.

    Args:
        user_barcode: Active user's barcode.
        item_barcode: The missing item's barcode.
        item_name:    Human-readable item name.
    """
    # ── REPLACE WITH REAL LOGIC ──────────────────────────────────────────────
    print(f"[BACKEND] Marked missing: user={user_barcode}, item={item_barcode} ({item_name})")
    # ─────────────────────────────────────────────────────────────────────────


# =====================================================
# APP
# =====================================================

class App(ctk.CTk):

    # How long (ms) to wait on non-ScanID pages before showing the timeout page
    SESSION_TIMEOUT_MS   = 30_000
    # How long (ms) the timeout warning page is shown before resetting
    TIMEOUT_DISMISS_MS   = 3_000
    # How long (ms) the FinalConfirmationPage is shown before resetting
    FINAL_CONFIRM_DISMISS_MS = 3_000

    def __init__(self):
        super().__init__()

        self.geometry("800x480")
        self.title("Barcode System")
        # self.attributes("-fullscreen", True)   # Uncomment on Raspberry Pi

        # ── Session state ────────────────────────────────────────────────────
        self.current_user_barcode: str | None = None
        # List of (item_name, item_barcode, borrowed_at) for the active user
        self.user_items: list[tuple[str, str, datetime]] = []

        self._timeout_job = None   # after() handle for the session timer

        # ── Build pages ──────────────────────────────────────────────────────
        self.frames = {}
        for F in (
            ScanIDPage,
            BorrowedItemsPage,
            ConfirmBorrowPage,
            ConfirmReturnPage,
            FinalConfirmationPage,
            SessionTimeoutPage,
        ):
            frame = F(self)
            self.frames[F.__name__] = frame
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.show_frame("ScanIDPage")

        # ── Wire up the simulated barcode entry (keyboard) ───────────────────
        # On a real scanner, replace this with whatever serial/HID input method
        # your scanner uses (e.g. read lines from /dev/ttyUSB0).
        self._barcode_buffer = ""
        self.bind("<Key>", self._on_key)

    # ── Navigation ───────────────────────────────────────────────────────────

    def show_frame(self, page_name: str) -> None:
        """Raise a page and manage the session timeout timer."""
        self.frames[page_name].tkraise()
        self._reset_timeout_timer(page_name)

    def _reset_timeout_timer(self, page_name: str) -> None:
        """Cancel any running timer; start a new one unless we're on ScanIDPage."""
        if self._timeout_job is not None:
            self.after_cancel(self._timeout_job)
            self._timeout_job = None

        if page_name not in ("ScanIDPage", "SessionTimeoutPage", "FinalConfirmationPage"):
            self._timeout_job = self.after(self.SESSION_TIMEOUT_MS, self._on_session_timeout)

    def _on_session_timeout(self) -> None:
        self._timeout_job = None
        self.show_frame("SessionTimeoutPage")
        self.after(self.TIMEOUT_DISMISS_MS, self.reset_session)

    # ── Session management ────────────────────────────────────────────────────

    def reset_session(self) -> None:
        """Clear all session state and return to ScanIDPage."""
        self.current_user_barcode = None
        self.user_items = []
        if self._timeout_job is not None:
            self.after_cancel(self._timeout_job)
            self._timeout_job = None
        self.show_frame("ScanIDPage")

    def start_final_confirmation(self) -> None:
        """Show FinalConfirmationPage, then reset after the dismiss delay."""
        self.show_frame("FinalConfirmationPage")
        self.after(self.FINAL_CONFIRM_DISMISS_MS, self.reset_session)

    # ── Barcode input routing ─────────────────────────────────────────────────

    def _on_key(self, event) -> None:
        """
        Accumulates keypresses into a barcode buffer.
        Most USB HID barcode scanners end their transmission with <Return>.
        Adjust the terminator if your scanner behaves differently.
        """
        if event.keysym == "Return":
            barcode = self._barcode_buffer.strip()
            self._barcode_buffer = ""
            if barcode:
                self._dispatch_barcode(barcode)
        elif event.char and event.char.isprintable():
            self._barcode_buffer += event.char

    def _dispatch_barcode(self, barcode: str) -> None:
        """
        Route a completed barcode scan based on the currently visible page.
        """
        current = self._current_page_name()

        if current == "ScanIDPage":
            self._handle_id_scan(barcode)

        elif current == "BorrowedItemsPage":
            self._handle_item_scan(barcode)

        # Scans on confirmation / timeout pages are intentionally ignored.

    def _current_page_name(self) -> str | None:
        """Return the name of whichever page is currently raised."""
        for name, frame in self.frames.items():
            try:
                if frame.winfo_ismapped():
                    return name
            except Exception:
                pass
        return None

    # ── Scan handlers ─────────────────────────────────────────────────────────

    def _handle_id_scan(self, user_barcode: str) -> None:
        self.current_user_barcode = user_barcode
        self.user_items = backend_get_user_items(user_barcode)
        self.frames["BorrowedItemsPage"].load(self.user_items)
        self.show_frame("BorrowedItemsPage")

    def _handle_item_scan(self, item_barcode: str) -> None:
        item_name, is_borrowed = backend_lookup_item(item_barcode, self.user_items)

        if is_borrowed:
            self.frames["ConfirmReturnPage"].load(item_name, item_barcode)
            self.show_frame("ConfirmReturnPage")
        else:
            self.frames["ConfirmBorrowPage"].load(item_name, item_barcode)
            self.show_frame("ConfirmBorrowPage")


# =====================================================
# PAGE 1: SCAN ID
# =====================================================

class ScanIDPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        dark_green  = "#2E7D32"
        light_green = "#81C784"
        self.configure(fg_color=dark_green)

        img = Image.open("green_corner.png")
        self.corner_tl = ctk.CTkImage(light_image=img,                          dark_image=img,                          size=(90, 90))
        self.corner_tr = ctk.CTkImage(light_image=img.rotate(270, expand=True), dark_image=img.rotate(270, expand=True), size=(90, 90))
        self.corner_bl = ctk.CTkImage(light_image=img.rotate(90,  expand=True), dark_image=img.rotate(90,  expand=True), size=(90, 90))
        self.corner_br = ctk.CTkImage(light_image=img.rotate(180, expand=True), dark_image=img.rotate(180, expand=True), size=(80, 80))

        ctk.CTkLabel(self, image=self.corner_tl, text="").place(relx=.2, rely=.2, anchor="center")
        ctk.CTkLabel(self, image=self.corner_tr, text="").place(relx=.8, rely=.2, anchor="center")
        ctk.CTkLabel(self, image=self.corner_bl, text="").place(relx=.2, rely=.8, anchor="center")
        ctk.CTkLabel(self, image=self.corner_br, text="").place(relx=.8, rely=.8, anchor="center")

        ctk.CTkLabel(
            self,
            text="SCAN ID",
            font=("Arial", 88, "bold"),
            text_color="white"
        ).place(relx=0.5, rely=0.5, anchor="center")


# =====================================================
# PAGE 2: BORROWED ITEMS
# =====================================================

class BorrowedItemsPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        ctk.CTkLabel(
            self,
            text="Current Borrowed Items",
            font=("Arial", 32, "bold")
        ).pack(pady=20)

        self.scroll_frame = ctk.CTkScrollableFrame(self, width=400, height=300)
        self.scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        ctk.CTkLabel(
            self,
            text="Scan an item to borrow or return",
            font=("Arial", 18)
        ).pack(side="bottom", pady=20)

        # Internal state: maps item_name → item_barcode for the current session
        self._item_barcodes: dict[str, str] = {}

    def load(self, items: list[tuple[str, str, datetime]]) -> None:
        """
        Populate the list from a fresh (item_name, item_barcode, borrowed_at) list.
        Call this every time the page is about to be shown.
        """
        self._item_barcodes = {name: bc for name, bc, _ in items}
        self._render(items)

    def remove_item(self, item_name: str) -> None:
        """
        Remove one item from the displayed list and internal map.
        Called after a return is confirmed or an item is marked missing.
        """
        self._item_barcodes.pop(item_name, None)
        # Rebuild display from remaining items (no dates needed here, use placeholders)
        # Re-render by asking the master for the current user_items minus this one
        master: App = self.master
        master.user_items = [(n, bc, dt) for n, bc, dt in master.user_items if n != item_name]
        self._render(master.user_items)

    def _render(self, items: list[tuple[str, str, datetime]]) -> None:
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        for item_name, item_barcode, borrowed_at in items:
            date_str = borrowed_at.strftime("%b %d, %Y  %H:%M")

            row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            row.pack(fill="x", pady=4, padx=10)

            ctk.CTkButton(
                row,
                text=f"• {item_name}",
                font=("Arial", 24),
                anchor="w",
                fg_color="transparent",
                text_color=("black", "white"),
                hover_color=("gray85", "gray25"),
                command=lambda n=item_name, bc=item_barcode: self._show_missing_popup(n, bc)
            ).pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                row,
                text=date_str,
                font=("Arial", 16),
                text_color=("gray40", "gray70"),
                anchor="e"
            ).pack(side="right", padx=(10, 0))

    def _show_missing_popup(self, item_name: str, item_barcode: str) -> None:
        master: App = self.master
        popup = ctk.CTkToplevel(self)
        popup.title("Mark as Missing")
        popup.overrideredirect(True)
        popup.update_idletasks()
        x = master.winfo_x() + (master.winfo_width()  // 2) - 150
        y = master.winfo_y() + (master.winfo_height() // 2) - 65
        popup.geometry(f"300x130+{x}+{y}")
        popup.grab_set()

        ctk.CTkLabel(
            popup,
            text=f"Mark '{item_name}' as missing?",
            font=("Arial", 16),
            wraplength=260
        ).pack(pady=20)

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack()

        ctk.CTkButton(
            btn_frame,
            text="Mark Missing",
            fg_color="red",
            hover_color="darkred",
            command=lambda: self._confirm_missing(item_name, item_barcode, popup)
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=popup.destroy
        ).pack(side="right", padx=10)

    def _confirm_missing(self, item_name: str, item_barcode: str, popup) -> None:
        master: App = self.master
        backend_mark_missing(master.current_user_barcode, item_barcode, item_name)
        popup.destroy()
        self.remove_item(item_name)
        # Stay on BorrowedItemsPage – reset the session timer
        master._reset_timeout_timer("BorrowedItemsPage")


# =====================================================
# PAGE 3: CONFIRM BORROW
# =====================================================

class ConfirmBorrowPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        ctk.CTkLabel(
            self,
            text="Borrow Item?",
            font=("Arial", 36, "bold")
        ).pack(pady=30)

        self.item_label = ctk.CTkLabel(self, text="", font=("Arial", 28))
        self.item_label.pack(pady=20)

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=40)

        ctk.CTkButton(
            button_frame,
            fg_color="#19ca63",
            hover_color="#219250",
            text="Confirm",
            font=("Arial", 30),
            width=180,
            height=60,
            command=self._on_confirm
        ).pack(side="left", padx=20)

        ctk.CTkButton(
            button_frame,
            fg_color="#cd2828",
            hover_color="#922121",
            text="Cancel",
            font=("Arial", 30),
            width=180,
            height=60,
            command=self._on_cancel
        ).pack(side="left", padx=20)

        self._item_name    = ""
        self._item_barcode = ""

    def load(self, item_name: str, item_barcode: str) -> None:
        """Set the item details before showing this page."""
        self._item_name    = item_name
        self._item_barcode = item_barcode
        self.item_label.configure(text=item_name)

    def _on_confirm(self) -> None:
        master: App = self.master
        backend_confirm_borrow(master.current_user_barcode, self._item_barcode, self._item_name)
        # Add to local session list so it shows up if the user comes back
        master.user_items.append((self._item_name, self._item_barcode, datetime.now()))
        master.start_final_confirmation()

    def _on_cancel(self) -> None:
        self.master.show_frame("BorrowedItemsPage")


# =====================================================
# PAGE 4: CONFIRM RETURN
# =====================================================

class ConfirmReturnPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        ctk.CTkLabel(
            self,
            text="Return Item?",
            font=("Arial", 36, "bold")
        ).pack(pady=30)

        self.item_label = ctk.CTkLabel(self, text="", font=("Arial", 28))
        self.item_label.pack(pady=20)

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=40)

        ctk.CTkButton(
            button_frame,
            fg_color="#19ca63",
            hover_color="#219250",
            text="Confirm",
            font=("Arial", 30),
            width=180,
            height=60,
            command=self._on_confirm
        ).pack(side="left", padx=20)

        ctk.CTkButton(
            button_frame,
            fg_color="#cd2828",
            hover_color="#922121",
            text="Cancel",
            font=("Arial", 30),
            width=180,
            height=60,
            command=self._on_cancel
        ).pack(side="left", padx=20)

        self._item_name    = ""
        self._item_barcode = ""

    def load(self, item_name: str, item_barcode: str) -> None:
        """Set the item details before showing this page."""
        self._item_name    = item_name
        self._item_barcode = item_barcode
        self.item_label.configure(text=item_name)

    def _on_confirm(self) -> None:
        master: App = self.master
        backend_confirm_return(master.current_user_barcode, self._item_barcode, self._item_name)
        self.master.frames["BorrowedItemsPage"].remove_item(self._item_name)
        master.start_final_confirmation()

    def _on_cancel(self) -> None:
        self.master.show_frame("BorrowedItemsPage")


# =====================================================
# PAGE 5: FINAL CONFIRMATION
# =====================================================

class FinalConfirmationPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        ctk.CTkLabel(
            self,
            text="Confirmed",
            font=("Arial", 80, "bold")
        ).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            self,
            text="Closing session..",
            font=("Arial", 30, "italic")
        ).place(relx=0.5, rely=0.7, anchor="center")


# =====================================================
# PAGE 6: SESSION TIMEOUT
# =====================================================

class SessionTimeoutPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        self.configure(fg_color="#1a1a2e")

        ctk.CTkLabel(
            self,
            text="Session Timed Out",
            font=("Arial", 60, "bold"),
            text_color="#e0e0e0"
        ).place(relx=0.5, rely=0.42, anchor="center")

        ctk.CTkLabel(
            self,
            text="Returning to start screen..",
            font=("Arial", 26, "italic"),
            text_color="#888888"
        ).place(relx=0.5, rely=0.62, anchor="center")


# =====================================================
# ENTRY POINT
# =====================================================

app = App()
app.mainloop()