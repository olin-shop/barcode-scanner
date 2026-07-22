"""
Main file for orchestrating the Barcode Scanner application.
Starts the Quart webhook backend/email scheduler in a background process,
and the CustomTkinter GUI in the main process.
"""

import multiprocessing
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
    quart_app.run(host=HOST_IP, port=PORT, use_reloader=False)


def run_gui() -> None:
    """Run the CustomTkinter GUI application."""
    app = App()
    app.mainloop()


def main() -> None:
    """
    Main orchestration method.
    """
    if sys.platform == "darwin":
        multiprocessing.set_start_method("spawn", force=True)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger.info("Starting barcode scanner application...")

    backend_process = multiprocessing.Process(target=run_backend, daemon=True)
    backend_process.start()

    try:
        run_gui()
    except KeyboardInterrupt:
        logger.info("Exiting...")
    finally:
        if backend_process.is_alive():
            backend_process.terminate()
            backend_process.join()

if __name__ == "__main__":
    main()
