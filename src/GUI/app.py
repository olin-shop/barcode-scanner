import asyncio
import logging
import queue
import threading
from typing import Any, Callable, Coroutine

import customtkinter as ctk

from GUI import gui_constants as const
from GUI.session_manager import SessionManager
from GUI.ScanIDPage import ScanIDPage
from GUI.BorrowedItemsPage import BorrowedItemsPage
from GUI.BorrowPage import ConfirmBorrowPage
from GUI.ReturnPage import ConfirmReturnPage
from GUI.ConfirmationPage import FinalConfirmationPage
from GUI.TimeoutPage import SessionTimeoutPage
from GUI.LoadingPage import LoadingPage
from GUI.popup import show_popup

logger = logging.getLogger(__name__)


class App(ctk.CTk):
    """
    Main application shell for the Olin Shop Barcode Scanner kiosk.
    Manages frame navigation, session timers, barcode HID inputs, and async background requests.
    """

    def __init__(self) -> None:
        super().__init__()

        # Appearance & Geometry
        ctk.set_appearance_mode("light")
        self.geometry(const.WINDOW_SIZE)
        self.title("Olin Shop Barcode Scanner")
        self.configure(fg_color=const.BG_LIGHT_BLUE)

        # Global Session State
        self.session = SessionManager()

        self._timeout_job = None   # after() handle for the session timer
        self._slide_job = None     # after() handle for slide transitions

        # Build pages
        self.frames = {}
        for F in (
            ScanIDPage,
            BorrowedItemsPage,
            ConfirmBorrowPage,
            ConfirmReturnPage,
            FinalConfirmationPage,
            SessionTimeoutPage,
            LoadingPage,
        ):
            frame = F(self)
            self.frames[F.__name__] = frame
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.current_page_name: str = "ScanIDPage"

        # Wire up simulated barcode HID scanner entry
        self._barcode_buffer = ""
        self.bind("<Key>", self._on_key)

        # Thread-safe queue for async background callbacks
        self._async_queue: queue.Queue = queue.Queue()
        self._poll_async_queue()

        # Background asyncio loop
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()

        # Show initial page
        self.show_frame("ScanIDPage")

    def _poll_async_queue(self) -> None:
        """Polls for callbacks queued by background async threads."""
        try:
            while not self._async_queue.empty():
                callback, result = self._async_queue.get_nowait()
                callback(result)
        except Exception as e:
            logger.error("Error processing async callback queue: %s", e, exc_info=True)
        finally:
            if self.winfo_exists():
                self.after(20, self._poll_async_queue)

    # Navigation

    def show_frame(self, page_name: str) -> None:
        """Raise a page with a smooth slide-in transition and manage the session timeout timer."""
        if self._slide_job is not None:
            try:
                self.after_cancel(self._slide_job)
            except Exception:
                pass
            self._slide_job = None

        self.current_page_name = page_name
        target_frame = self.frames[page_name]

        # Ensure all non-target frames remain in full position
        for name, frame in self.frames.items():
            if name != page_name:
                try:
                    frame.place(relx=0, rely=0, relwidth=1, relheight=1)
                except Exception:
                    pass

        target_frame.tkraise()

        # Smooth High-FPS Slide-In transition curve (ease-out push over ~240ms at ~125 FPS)
        steps = 0
        step_idx = 0

        def _animate_slide():
            nonlocal step_idx
            if not self.winfo_exists():
                return
            step_idx += 1
            if step_idx <= steps:
                progress = step_idx / steps
                ease_out = 1.0 - (1.0 - progress) ** 2.5
                rel_x = 1.0 - ease_out

                if target_frame.winfo_exists():
                    target_frame.place(relx=rel_x, rely=0, relwidth=1, relheight=1)
                    self._slide_job = self.after(8, _animate_slide)
            else:
                target_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
                self._slide_job = None

        target_frame.place(relx=1.0, rely=0, relwidth=1, relheight=1)
        self.update_idletasks()
        _animate_slide()
        self._reset_timeout_timer(page_name)

    def _reset_timeout_timer(self, page_name: str) -> None:
        """Cancel any running timer; start a new one unless we're on ScanIDPage."""
        if self._timeout_job is not None:
            self.after_cancel(self._timeout_job)
            self._timeout_job = None

        if page_name not in ("ScanIDPage", "SessionTimeoutPage", "FinalConfirmationPage"):
            self._timeout_job = self.after(const.SESSION_TIMEOUT_MS, self._on_session_timeout)

    def _on_session_timeout(self) -> None:
        logger.info("Session timed out for user=%s", self.session.current_user_barcode)
        self._timeout_job = None
        self.show_frame("SessionTimeoutPage")
        self.after(const.TIMEOUT_DISMISS_MS, self.reset_session)

    # Session management

    def reset_session(self) -> None:
        """Clear all session state and return to ScanIDPage."""
        self.session.reset()
        if self._timeout_job is not None:
            self.after_cancel(self._timeout_job)
            self._timeout_job = None
        self.show_frame("ScanIDPage")

    def start_final_confirmation(self) -> None:
        """Show FinalConfirmationPage, then reset after the dismiss delay."""
        self.show_frame("FinalConfirmationPage")
        self.after(const.FINAL_CONFIRM_DISMISS_MS, self.reset_session)

    def display_popup(self, text: str) -> ctk.CTkToplevel:
        """Display a centered, frameless warning popup with rounded corners and a close button."""
        return show_popup(text, self)

    def show_popup(self, text: str) -> ctk.CTkToplevel:
        """Display a centered, frameless warning popup with rounded corners and a close button."""
        return show_popup(text, self)

    # Barcode input routing

    def _on_key(self, event) -> None:
        """
        Accumulates keypresses into a barcode buffer.
        Most USB HID barcode scanners end their transmission with <Return>.
        """
        if event.keysym == "Return":
            barcode = self._barcode_buffer.strip()
            self._barcode_buffer = ""
            if barcode:
                self._dispatch_barcode(barcode)
        elif event.char and event.char.isprintable():
            self._barcode_buffer += event.char

    def _dispatch_barcode(self, barcode: str) -> None:
        """Route a completed barcode scan based on the currently visible page."""
        current = self._current_page_name()

        if current == "ScanIDPage":
            self._handle_id_scan(barcode)
        elif current == "BorrowedItemsPage":
            self._handle_item_scan(barcode)

    def _current_page_name(self) -> str | None:
        """Return the name of whichever page is currently raised."""
        if hasattr(self, "current_page_name") and self.current_page_name:
            return self.current_page_name
        for name, frame in self.frames.items():
            try:
                if frame.winfo_ismapped():
                    return name
            except Exception:
                logger.debug("Could not check mapped state for %s", name, exc_info=True)
        return None

    # Scan handlers

    def _handle_id_scan(self, user_barcode: str) -> None:
        logger.info("Scanned user id: %s", user_barcode)
        self.run_async_with_loading(
            self.session.start_session(user_barcode),
            self._on_user_items_loaded,
        )

    def _on_user_items_loaded(self, items) -> None:
        if self._current_page_name() in ("SessionTimeoutPage", "FinalConfirmationPage"):
            logger.info("Ignoring stale user-items response; session moved on.")
            return
        self.frames["BorrowedItemsPage"].load(items, user_name=self.session.current_user_name)
        self.show_frame("BorrowedItemsPage")

    def _handle_item_scan(self, item_barcode: str) -> None:
        logger.info("Scanned item id: %s", item_barcode)
        self.run_async_with_loading(
            self.session.lookup_item(item_barcode),
            lambda result: self._on_item_looked_up(result, item_barcode),
        )

    def _on_item_looked_up(self, result: tuple[str, bool], item_barcode: str) -> None:
        if self._current_page_name() in ("SessionTimeoutPage", "FinalConfirmationPage"):
            logger.info("Ignoring stale item-lookup response; session moved on.")
            return

        item_name, is_borrowed = result
        if is_borrowed:
            self.frames["ConfirmReturnPage"].load(item_name, item_barcode)
            self.show_frame("ConfirmReturnPage")
        else:
            self.frames["ConfirmBorrowPage"].load(item_name, item_barcode)
            self.show_frame("ConfirmBorrowPage")

    def run_async(self, coro: Coroutine[Any, Any, Any], callback: Callable[[Any], None]) -> None:
        """
        Submit a coroutine; call callback(result) on the main thread when done.
        """
        def _on_done(f: asyncio.Future) -> None:
            try:
                res = f.result()
                self._async_queue.put((callback, res))
            except Exception as e:
                logger.error("Async execution error: %s", e, exc_info=True)

        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        future.add_done_callback(_on_done)

    def run_async_with_loading(
        self,
        coro: Coroutine[Any, Any, Any],
        callback: Callable[[Any], None],
        threshold_ms: int = 1000,
    ) -> None:
        """
        Submits a coroutine. Shows 'LoadingPage' only if execution takes longer than threshold_ms (1s).
        Prevents screen flickering for fast/cached operations.
        """
        loading_job = self.after(threshold_ms, lambda: self.show_frame("LoadingPage"))

        def _wrapped_callback(result: Any) -> None:
            if loading_job is not None:
                try:
                    self.after_cancel(loading_job)
                except Exception:
                    pass
            callback(result)

        self.run_async(coro, _wrapped_callback)


if __name__ == "__main__":
    app = App()
    app.mainloop()
