import customtkinter as ctk
from datetime import datetime

# Async
import asyncio, threading

#
from GUI.ScanIDPage import ScanIDPage
from GUI.TimeoutPage import SessionTimeoutPage
from GUI.ReturnPage import ConfirmReturnPage
from GUI.BorrowPage import ConfirmBorrowPage
from GUI.BorrowedItemsPage import BorrowedItemsPage
from GUI.ConfirmationPage import FinalConfirmationPage
from GUI.LoadingPage import LoadingPage

from backend.backend_types import Status, UserInfoPayload
from backend.requests import get_name, get_item, checkout
from backend.backend_constants import min_datetime

# =====================================================
# BACKEND HOOKS
# Replace each function body with your real logic.
# =====================================================
_current_user_name: str = ""
_current_user_email: str = ""


def _to_item_id(item_barcode: str) -> int:
    """convertubg scanned barcode string to the int Item ID
    the backend pipeline expects. Falls back to 0 if it isn't numeric."""
    try:
        return int(item_barcode)
    except (TypeError, ValueError):
        return 0
    
def backend_get_user_items(user_barcode: str) -> list[tuple[ str, datetime]]:
    """
    Called after a user ID is scanned.

    Args:
        user_barcode: The raw barcode string from the scanner.

    Returns:
        List of (item_name, item_barcode, borrowed_at) tuples for all items
        currently borrowed by this user.
        Return an empty list if the user has no borrowed items.
    """
    global _current_user_name, _current_user_email

    name, email, time_borrowed, statuses, item_ids = asyncio.run(get_name(user_barcode))
    _current_user_name = name
    _current_user_email = email

    # get_name() only gives us item barcodes (item_ids) for currently
    # borrowed items, not names - names are resolved on demand elsewhere
    # (e.g. get_item(), the same call BorrowedItemsPage's "Mark as Missing"
    # popup already uses). We put the barcode in both tuple slots here so
    # the rest of the app - which expects an
    # (item_name, item_barcode, borrowed_at) shape - keeps working.
    return [
        (str(item_id), str(item_id), borrowed_at)
        for item_id, borrowed_at in zip(item_ids, time_borrowed)
    ]
    # --------------------------------------------


def backend_lookup_item(item_barcode: str, user_items: list[tuple[str, str, datetime]]) -> tuple[str, bool]:
    """
    Called when an item barcode is scanned on the BorrowedItemsPage.

    Args:
        item_barcode:  The raw barcode string from the scanner.
        user_items:    The current list of (item_name, item_barcode, borrowed_at)
                       tuples for the active user.

    Returns:
        (item_name, is_borrowed) where:
            item_name    human-readable name for the item
            is_borrowed  True  → item is already borrowed by this user → show ConfirmReturnPage
                         False → item is new                           → show ConfirmBorrowPage
    """
    item_name, status = asyncio.run(get_item(item_barcode))

    if not item_name:
        # Backend didn't recognize the barcode or timed out
        return f"Item ({item_barcode})", False

    already_borrowed = status == Status.BORROWED or any(
        name == item_name for name, _, _ in user_items
    )
    return item_name, already_borrowed
    # --------------------------------


def backend_confirm_borrow(user_barcode: str, item_barcode: str, item_name: str) -> None:
    """
    Called when the user confirms borrowing a new item.

    Args:
        user_barcode: Active user's barcode.
        item_barcode: The item being borrowed.
        item_name:    Human-readable item name.
    """
    user_info: UserInfoPayload = {
        "name": _current_user_name,
        "user_id": user_barcode,
        "email": _current_user_email,
        "item_id": _to_item_id(item_barcode),
        "borrowed_date": datetime.now(),
        "returned_date": min_datetime,
        "item_status": Status.BORROWED,
    }
    success = asyncio.run(checkout(user_info))
    if not success:
        print(f"[BACKEND] Borrow failed to send: user={user_barcode}, item={item_barcode} ({item_name})")

def backend_confirm_return(user_barcode: str, item_barcode: str, item_name: str) -> None:
    """
    Called when the user confirms returning a borrowed item.

    Args:
        user_barcode: Active user's barcode.
        item_barcode: The item being returned.
        item_name:    Human-readable item name.
    """
    user_info: UserInfoPayload = {
        "name": _current_user_name,
        "user_id": user_barcode,
        "email": _current_user_email,
        "item_id": _to_item_id(item_barcode),
        "borrowed_date": min_datetime,
        "returned_date": datetime.now(),
        "item_status": Status.INSTOCK,
    }
    success = asyncio.run(checkout(user_info))
    if not success:
        print(f"[BACKEND] Return failed to send: user={user_barcode}, item={item_barcode} ({item_name})")
    # -----------------------


def backend_mark_missing(user_barcode: str, item_barcode: str, item_name: str) -> None:
    """
    Called when the user marks a borrowed item as missing.

    Args:
        user_barcode: Active user's barcode.
        item_barcode: The missing item's barcode.
        item_name:    Human-readable item name.
    """
    user_info: UserInfoPayload = {
        "name": _current_user_name,
        "user_id": user_barcode,
        "email": _current_user_email,
        "item_id": _to_item_id(item_barcode),
        "borrowed_date": min_datetime,
        "returned_date": datetime.now(),
        "item_status": Status.MISSING,
    }
    success = asyncio.run(checkout(user_info))
    if not success:
        print(f"[BACKEND] Mark-missing failed to send: user={user_barcode}, item={item_barcode} ({item_name})")
    #------------------------------------

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

        # Session state
        self.current_user_barcode: str | None = None
        # List of (item_name, item_barcode, borrowed_at) for the active user
        self.user_items: list[tuple[str, str, datetime]] = []

        self._timeout_job = None   # after() handle for the session timer

        # Build pages 
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

        # Wire up the simulated barcode entry (keyboard) 
        # On a real scanner, replace this with whatever serial/HID input method
        # your scanner uses (e.g. read lines from /dev/ttyUSB0).
        self._barcode_buffer = ""
        self.bind("<Key>", self._on_key)
        # Async loop
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()


    # Navigation

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

    # Session management

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

    # Barcode input routing

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

    # Scan handlers 

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

    # make asyncronous ?
    def run_async(self, coro, callback):
        """Submit a coroutine; call callback(result) on the main thread when done."""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        future.add_done_callback(
            lambda f: self.after(0, callback, f.result())
        )
        


app = App()
app.mainloop()