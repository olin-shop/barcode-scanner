"""
Types for the backend.
"""

from enum import StrEnum
from typing import TypedDict
from datetime import datetime


class Status(StrEnum):
    """
    String enum for status types.
    """

    BORROWED = "Borrowed"
    MISSING = "Missing"
    INSTOCK = "In Stock"
    NONE = "None"


class UserInfoPayload(TypedDict):
    """
    Type defined for the user information dictionary.
    """

    first_name: str
    last_name: str
    id: str
    email: str
    item_id: int
    borrowed_date: datetime
    status: Status
