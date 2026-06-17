"""
Accessible constants for the backend.
"""

from dotenv import dotenv_values

config: dict = dotenv_values(".env")

NAME_URL: str = config["NAME_URL"]

ITEM_URL: str = config["ITEM_URL"]

CHECKOUT_URL: str = config["CHECKOUT_URL"]

BORROWED_ITEMS_URL: str = config["BORROWED_ITEMS_URL"]

PORT: int = config["PORT"]

HOST_IP: str = config["HOST_IP"]
