"""
Main file.
"""

from backend.endpoints import flask_app
from backend.backend_constants import HOST_IP, PORT


def main() -> None:
    """
    Main method.
    """
    flask_app.run(host=HOST_IP, port=PORT)


if __name__ == "__main__":
    main()
