"""
Types for the backend.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Optional, TypedDict

@dataclass
class BorrowedItem:
    name: str
    barcode: str
    borrowed_at: datetime

def to_item_id(barcode: str) -> Optional[int]:
    try:
        return int(barcode)
    except ValueError:
        return None


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
    item_status: Status
