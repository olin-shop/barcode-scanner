"""
Unit tests for the backend outgoing requests (requests.py).
Utilizes a FakeDatabase and a mock Power Automate integration to verify the async
flow, concurrency, error states, and overall routing architecture.
"""
import pytest
import asyncio
from datetime import datetime
from backend.backend_types import Status, UserInfoPayload
from backend.requests import get_name, get_item, checkout, request_borrowed_items
from backend.backend_constants import min_datetime, to_excel_date
from backend.app_state import pending_requests

from quart.testing import QuartClient
from pytest_mock.plugin import MockerFixture

class FakeResponse:
    """Mock for the requests.post response."""
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code

class FakeDatabase:
    """
    Simulates the SharePoint / Excel sheet database that Power Automate interacts with.
    """
    def __init__(self) -> None:
        self.users = {
            "OL01509": {"Name": "John Doe", "Email": "jdoe@olin.edu"},
            "OL999": {"Name": "Alice Smith", "Email": "asmith@olin.edu"}
        }
        self.items = {
            11134: {"ItemName": "Power Drill", "ItemStatus": "In Stock"},
            123: {"ItemName": "Screwdriver", "ItemStatus": "Borrowed"}
        }
        self.active_checkouts = {
            123: {
                "Name": "John Doe", 
                "Email": "jdoe@olin.edu", 
                "UserID": "OL01509", 
                "ItemID": 123, 
                "DateBorrowed": 45000.0, 
                "DateReturned": to_excel_date(min_datetime), 
                "ItemStatus": "Borrowed"
            }
        }

    def checkout(self, item_id: int, user_id: str, status: str, date_borrowed: float) -> None:
        """Process a checkout action in the mock DB."""
        if item_id in self.items:
            self.items[item_id]["ItemStatus"] = status
            
            user_info = self.users.get(user_id, {"Name": "Unknown", "Email": ""})
            
            if status == "Borrowed":
                self.active_checkouts[item_id] = {
                    "Name": user_info["Name"],
                    "Email": user_info["Email"],
                    "UserID": user_id,
                    "ItemID": item_id,
                    "DateBorrowed": date_borrowed or to_excel_date(min_datetime),
                    "DateReturned": to_excel_date(min_datetime),
                    "ItemStatus": status
                }
            else:
                self.active_checkouts.pop(item_id, None)

    def get_all_borrowed(self) -> list[dict]:
        """Fetch all currently active checkouts."""
        return list(self.active_checkouts.values())

    def get_user_history(self, user_id: str) -> list[dict]:
        """Fetch all checkout history for a specific user."""
        return [
            data for data in self.active_checkouts.values() 
            if data.get("UserID") == user_id
        ]

@pytest.fixture
def fake_db() -> FakeDatabase:
    """Fixture that provides a fresh FakeDatabase instance."""
    return FakeDatabase()

@pytest.fixture
def fake_power_automate(client: QuartClient, mocker: MockerFixture, fake_db: FakeDatabase) -> None:
    """
    Simulates the Power Automate webhook callbacks by intercepting requests.post,
    querying/updating the FakeDatabase, and sending the callback via Quart test client.
    """
    async def mock_post(url: str, json: dict, timeout: int) -> FakeResponse:
        req_id = json.get("RequestID")
        
        async def trigger_callback() -> None:
            try:
                
                if "UserID" in json and "ItemID" in json and "ItemStatus" in json:
                    fake_db.checkout(
                        json.get("ItemID"), 
                        json.get("UserID"), 
                        json.get("ItemStatus"), 
                        json.get("DateBorrowed")
                    )
                    await client.post("/checkout", json={"RequestID": req_id, "Sent": "Received"})
                    
                elif "ItemID" in json and "ItemStatus" not in json:
                    item_id = int(json.get("ItemID", 0))
                    item_data = fake_db.items.get(item_id, {"ItemName": "Unknown", "ItemStatus": "None"})
                    await client.post("/items", json={
                        "RequestID": req_id,
                        "ItemName": item_data["ItemName"],
                        "ItemStatus": item_data["ItemStatus"]
                    })
                    
                elif "UserID" in json and "ItemID" not in json:
                    user_id = json.get("UserID")
                    user_data = fake_db.users.get(user_id, {"Name": "Unknown", "Email": ""})
                    await client.post("/names", json={
                        "RequestID": req_id,
                        "Name": user_data["Name"],
                        "Email": user_data["Email"],
                        "excelData": fake_db.get_user_history(user_id)
                    })
                    
                else:
                    await client.post("/borrowed-items", json={
                        "RequestID": req_id,
                        "excelData": fake_db.get_all_borrowed()
                    })
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"ERROR IN CALLBACK: {e}")

        await trigger_callback()
        
        return FakeResponse(200)

    mocker.patch("backend.requests.requests.post", side_effect=mock_post)
    return fake_db

@pytest.mark.asyncio
async def test_get_name_flow(fake_power_automate: None) -> None:
    """Verifies that calling get_name successfully retrieves user info from the mock DB."""
    res = await get_name("OL01509")
    assert res is not None
    name, email, dates, statuses, ids = res
    assert name == "John Doe"
    assert email == "jdoe@olin.edu"
    assert ids == [123]

@pytest.mark.asyncio
async def test_get_item_flow(fake_power_automate: None) -> None:
    """Verifies that calling get_item successfully retrieves item info from the mock DB."""
    res = await get_item(11134)
    assert res is not None
    item_name, item_status = res
    assert item_name == "Power Drill"
    assert item_status == Status.INSTOCK

@pytest.mark.asyncio
async def test_checkout_and_request_borrowed(fake_power_automate: None) -> None:
    """Tests the full flow of checking out an item and requesting the borrowed items list."""
    res_borrowed_initial = await request_borrowed_items()
    _, _, ids = res_borrowed_initial
    assert 11134 not in ids
    
    payload: UserInfoPayload = {
        "name": "Alice Smith",
        "user_id": "OL999",
        "email": "asmith@olin.edu",
        "item_id": 11134,
        "borrowed_date": datetime.now(),
        "returned_date": min_datetime,
        "item_status": Status.BORROWED
    }
    success = await checkout(payload)
    assert success is True
    
    res_borrowed_after = await request_borrowed_items()
    _, statuses, ids = res_borrowed_after
    
    drill_index = ids.index(11134)
    assert statuses[drill_index] == Status.BORROWED

@pytest.mark.asyncio
async def test_unknown_user_flow(fake_power_automate: None) -> None:
    """Test that an unknown barcode correctly maps to our 'Unknown' mock default."""
    res = await get_name("INVALID_BARCODE")
    assert res is not None
    name, email, _, _, _ = res
    assert name == "Unknown"
    assert email == ""

@pytest.mark.asyncio
async def test_power_automate_failure_500(mocker: MockerFixture) -> None:
    """Ensure we gracefully return False/None if Power Automate throws a 500 server error."""
    async def mock_fail(*args: tuple, **kwargs: dict) -> FakeResponse:
        return FakeResponse(500)
    
    mocker.patch("backend.requests.requests.post", side_effect=mock_fail)
    
    res = await get_item(11134)
    assert res is None
    
    assert len(pending_requests) == 0

@pytest.mark.asyncio
async def test_power_automate_timeout(mocker: MockerFixture) -> None:
    """Ensure we gracefully return False/None if the Future times out without a callback."""
    async def mock_timeout(*args: tuple, **kwargs: dict) -> FakeResponse:
        return FakeResponse(200) # Accepts, but no callback is ever sent
    
    mocker.patch("backend.requests.requests.post", side_effect=mock_timeout)
    mocker.patch("backend.requests.asyncio.wait_for", side_effect=asyncio.TimeoutError)
    
    res = await get_name("OL01509")
    assert res is None
    
    assert len(pending_requests) == 0

@pytest.mark.asyncio
async def test_high_concurrency_get_item(fake_power_automate: None) -> None:
    """
    Test sending 50 concurrent requests for get_item.
    Since they all fire simultaneously, this validates the Correlation ID architecture 
    can properly route 50 distinct asynchronous callbacks to their correct Futures.
    """
    tasks = [get_item(11134) for _ in range(50)]
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 50
    for res in results:
        assert res is not None
        item_name, item_status = res
        assert item_name == "Power Drill"
        assert item_status == Status.INSTOCK
    
    # Ensure no lingering pending requests
    assert len(pending_requests) == 0
