"""
Unit tests for backend/http_client.py (the httpx replacement for requests-async)
and for how requests.py turns HTTP failures into "request failed" results.
"""

import json

import httpx
import pytest
from pytest_mock import MockerFixture

from backend.app_state import pending_requests
from backend.http_client import HTTP_ERRORS, MAYBE_DELIVERED_ERRORS, post_json
from backend.requests import get_item


@pytest.mark.asyncio
async def test_post_json_sends_body_and_headers() -> None:
    """post_json POSTs the JSON body with the given headers and returns the response."""
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["body"] = json.loads(request.content)
        seen["key"] = request.headers.get("x-api-key")
        return httpx.Response(202)

    res = await post_json(
        "https://flow.example/trigger",
        json={"ItemID": 11134, "RequestID": "r1"},
        headers={"x-api-key": "k1"},
        timeout=5,
        transport=httpx.MockTransport(handler),
    )

    assert res.status_code == 202
    assert seen == {"method": "POST", "body": {"ItemID": 11134, "RequestID": "r1"}, "key": "k1"}


@pytest.mark.asyncio
async def test_post_json_network_error_is_an_http_error() -> None:
    """A connection failure raises an exception that callers catch via HTTP_ERRORS."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route to host", request=request)

    with pytest.raises(HTTP_ERRORS):
        await post_json(
            "https://flow.example/trigger",
            json={},
            transport=httpx.MockTransport(handler),
        )


@pytest.mark.asyncio
async def test_post_json_bad_url_is_an_http_error() -> None:
    """A malformed URL from .env is caught by HTTP_ERRORS too, instead of crashing."""
    with pytest.raises(HTTP_ERRORS):
        await post_json("http://[not-a-host", json={})


def test_maybe_delivered_errors_are_http_errors() -> None:
    """Every 'maybe delivered' error is also an HTTP error, so it is always caught."""
    for err in MAYBE_DELIVERED_ERRORS:
        assert issubclass(err, httpx.HTTPError)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectError("refused"),
        httpx.ConnectTimeout("slow"),
        httpx.ReadTimeout("no reply"),
    ],
)
async def test_http_failure_returns_none_and_cleans_up(
    mocker: MockerFixture, error: Exception
) -> None:
    """requests.py returns None on any httpx failure and leaves no pending request."""
    mocker.patch("backend.requests.post_json", side_effect=error)

    assert await get_item(11134) is None
    assert len(pending_requests) == 0
