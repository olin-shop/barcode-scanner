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
    """Run the Quart backend and its attached APScheduler in a background thread."""
    import asyncio
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    config = Config()
    config.bind = [f"0.0.0.0:{PORT}"]

    try:
        logger.info("Starting Hypercorn backend server on 0.0.0.0:%d...", PORT)
        loop.run_until_complete(serve(quart_app, config))
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
