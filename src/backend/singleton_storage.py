"""
Classes used to store and clear the currently accessed data sent from the database pipelines.
"""

from typing import Any
from threading import Lock
from datetime import datetime

from backend.backend_types import Status
from backend.backend_constants import min_datetime


class SingletonMeta(type):
    """
    Metaclass for creating singleton pattern.
    """

    _instances = {}
    _lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)

        return cls._instances[cls]


class BaseStorage(metaclass=SingletonMeta):
    """
    Base class for the storage type.
    Defines the basic logic for singleton access, storing and clearing.
    """

    def clear(self) -> None:
        """
        Clears all of the attributes in a given storage class.
        """
        for key in self.__dict__:
            if not key.startswith("_"):
                setattr(self, key, None)

    def provide_data(self, **kwargs) -> None:
        """
        Gathers validated data and commits it to the storage.
        """
        useful_items: dict = self._validate_data(**kwargs)

        for key in useful_items:
            setattr(self, key, useful_items[key])

    def get_data(self, item: str, default: Any = None) -> Any:
        """
        Gets data from the storage and returns it, with an optional default.

        Parameters
        ----------
        item : str
            The data name you are looking for.
        default : Any, optional
            An optional selection to give a default value.
        Returns
        -------
        Any
            The data that you need.
        """
        value: Any = getattr(self, item, default)

        return value

    def _validate_data(self, **kwargs) -> dict:
        raise NotImplementedError()


class CheckoutStorage(BaseStorage):
    """
    Subclass of BaseStorage, specifically for the checkout.
    """

    name: str = ""
    user_id: str = ""
    email: str = ""
    item_id: int = 0
    borrowed_date: datetime = min_datetime
    returned_date: datetime = min_datetime
    item_status: Status = Status.NONE

    # When the data has been received, this will be True.
    has_been_sent: bool = False

    # When changed, this will be True. Otherwise, False
    on_change: bool = False

    safe_values: set[str] = {
        "name",
        "user_id",
        "email",
        "item_id",
        "borrowed_date",
        "returned_date",
        "item_status",
        "has_been_sent",
    }

    def _validate_data(self, **kwargs) -> dict:
        safe_values_dict: dict = {}
        for keyword, value in kwargs.items():
            if keyword in CheckoutStorage.safe_values:
                safe_values_dict[keyword] = value

        return safe_values_dict


class NameStorage(BaseStorage):
    """
    Subclass of BaseStorage, specifically for collecting names and emails.
    """

    name: str = ""
    email: str = ""
    time_borrowed: list[datetime] = []
    statuses: list[Status] = []
    item_ids: list[int] = []

    # When changed, this will be True. Otherwise, False
    on_change: bool = False

    safe_values: set[str] = {
        "name",
        "email",
        "time_borrowed",
        "statuses",
        "item_ids",
    }

    def _validate_data(self, **kwargs) -> dict:
        safe_values_dict: dict = {}
        for keyword, value in kwargs.items():
            if keyword in NameStorage.safe_values:
                safe_values_dict[keyword] = value

        return safe_values_dict


class ItemStorage(BaseStorage):
    """
    Subclass of BaseStorage, specifically for storing items.
    """

    item_id: int = 0
    item_name: str = ""
    item_status: Status = Status.NONE

    # When changed, this will be True. Otherwise, False
    on_change: bool = False

    safe_values: set[str] = {"item_id", "item_name", "item_status"}

    def _validate_data(self, **kwargs) -> dict:
        safe_values_dict: dict = {}
        for keyword, value in kwargs.items():
            if keyword in ItemStorage.safe_values:
                safe_values_dict[keyword] = value

        return safe_values_dict


class BorrowedItemsStorage(BaseStorage):
    """
    Subclass of BaseStorage, specifically for storing borrowed items.
    """

    item_ids: list[int] = []
    time_borrowed: list[datetime] = []
    statuses: list[Status] = []

    # When changed, this will be True. Otherwise, False
    on_change: bool = False

    safe_values: set[str] = {"time_borrowed", "statuses", "item_ids"}

    def _validate_data(self, **kwargs) -> dict:
        safe_values_dict: dict = {}
        for keyword, value in kwargs.items():
            if keyword in BorrowedItemsStorage.safe_values:
                safe_values_dict[keyword] = value

        return safe_values_dict
