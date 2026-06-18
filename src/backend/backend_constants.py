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

TIMEOUT: int = 10

db_to_class_conversion: dict[str, str] = {
    "First Name": "first_name",
    "Last Name": "last_name",
    "ID": "id",
    "Email": "email",
    "Date Borrowed": "borrowed_date",
    "Status": "status",
    "Item Name": "item_name",
}
