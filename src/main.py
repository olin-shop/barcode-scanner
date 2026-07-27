"""
Main file for orchestrating the Barcode Scanner application.
Starts the Quart webhook backend/email scheduler in a background thread,
and the CustomTkinter GUI in the main thread.
"""

import threading
import sys
import logging

from backend.endpoints import quart_app
from backend.backend_constants import HOST_IP, PORT
from Email.email_service import start_email_scheduler
from GUI.app import App

logger = logging.getLogger(__name__)


@quart_app.before_serving
async def startup() -> None:
    """Initialize the email scheduler right before Quart starts serving requests."""
    start_email_scheduler()


def run_backend() -> None:
    """Run the Quart backend and its attached APScheduler."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # Bind to 0.0.0.0 so ngrok, localhost, and local IPs reach port 5000 cleanly
        host = "0.0.0.0" if HOST_IP in ("127.0.0.1", "localhost") else HOST_IP
        quart_app.run(host=host, port=PORT, use_reloader=False)
    except Exception as e:
        logger.error("Backend server error: %s", e, exc_info=True)


def run_gui() -> None:
    """Run the CustomTkinter GUI application."""
    app = App()
    app.mainloop()


def main() -> None:
    """
    Main orchestration method.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger.info("Starting barcode scanner application...")

    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()

    try:
        run_gui()
    except KeyboardInterrupt:
        logger.info("Exiting...")


if __name__ == "__main__":
    main()
