"""
Main file.
"""

from backend.endpoints import quart_app
from backend.backend_constants import HOST_IP, PORT


def main() -> None:
    """
    Main method.
    """
    # Quart automatically manages the asyncio event loop for you
    quart_app.run(host=HOST_IP, port=PORT)


if __name__ == "__main__":
    main()
