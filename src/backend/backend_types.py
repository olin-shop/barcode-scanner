"""
Types for the backend.
"""

from enum import StrEnum


class Status(StrEnum):
    """
    String enum for status types.
    """

    BORROWED = "Borrowed"
    MISSING = "Missing"
    INSTOCK = "In Stock"
    NONE = "None"
