"""
Accessible constants for the backend.
"""

from datetime import datetime, timedelta

from dotenv import dotenv_values

config: dict = dotenv_values(".env")

NAME_URL: str = config["NAME_URL"]

ITEM_URL: str = config["ITEM_URL"]

CHECKOUT_URL: str = config["CHECKOUT_URL"]

BORROWED_ITEMS_URL: str = config["BORROWED_ITEMS_URL"]

PORT: int = config["PORT"]

HOST_IP: str = config["HOST_IP"]

TIMEOUT: int = 10

# --- Overdue-item email reminders ---------------------------------------

SMTP_HOST: str = config.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(config.get("SMTP_PORT", 587))
SMTP_USERNAME: str = config.get("SMTP_USERNAME", "")
SMTP_PASSWORD: str = config.get("SMTP_PASSWORD", "")
FROM_EMAIL: str = config.get("FROM_EMAIL", SMTP_USERNAME)

# An item is considered overdue once it's been borrowed longer than this.
OVERDUE_AFTER_DAYS: int = int(config.get("OVERDUE_AFTER_DAYS", 14))

# Local hour (0-23) at which the daily overdue check/reminder run fires.
REMINDER_HOUR: int = int(config.get("REMINDER_HOUR", 8))

db_to_class_conversion: dict[str, str] = {
    "Name": "name",
    "UserID": "user_id",
    "Email": "email",
    "DateBorrowed": "borrowed_date",
    "DateReturned": "returned_date",
    "ItemID": "item_id",
    "ItemName": "item_name",
    "ItemStatus": "item_status",
}

# January 1st, 2000 at 12:00AM
min_datetime: datetime = datetime(2000, 1, 1, 0, 0, 0)


def from_excel_date(num: float) -> datetime:
    """
    Takes a float in excel date format and converts it into datetime.
    """

    # Base date accounting for Excel's 1900 leap year bug
    excel_base: datetime = datetime(1899, 12, 30, 0, 0, 0)

    # Convert the float into a time difference of days
    delta = timedelta(days=num)

    # Add the timedelta back to the base date
    return excel_base + delta


def to_excel_date(dt: datetime) -> float:
    """
    Takes a datetime and converts it to excel's number format.
    """

    # Base date accounting for Excel's 1900 leap year bug
    excel_base: datetime = datetime(1899, 12, 30, 0, 0, 0)

    delta = dt - excel_base

    # Calculate days + fractional day for time
    return delta.days + (delta.seconds + delta.microseconds / 1e6) / 86400
