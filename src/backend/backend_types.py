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

    name: str
    user_id: str
    email: str
    item_id: int
    borrowed_date: datetime
    returned_date: datetime
    status: Status
