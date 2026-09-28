"""
Async HTTP helper for posting to the Power Automate flows.

Replaces the archived requests-async library (itself a thin wrapper around httpx)
with httpx directly. A new client is opened for every call because requests are made
from two different event loops (the GUI's background loop and the Quart/scheduler
loop), and an httpx.AsyncClient must never be shared across event loops.
"""

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# httpx and httpcore log every request URL at INFO. The flow trigger URLs carry a
# "sig" secret that lets anyone run the flow, so keep them out of the kiosk log.
for _noisy in ("httpx", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

# Everything httpx can raise while sending a request. httpx.InvalidURL is listed
# separately because it does not inherit from httpx.HTTPError.
HTTP_ERRORS: tuple[type[BaseException], ...] = (httpx.HTTPError, httpx.InvalidURL)

# Errors raised after the request may already have reached Power Automate, so the flow
# might have run even though we never saw a response.
MAYBE_DELIVERED_ERRORS: tuple[type[BaseException], ...] = (
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.ReadError,
    httpx.RemoteProtocolError,
)


async def post_json(
    url: str,
    json: dict[str, Any],
    headers: Optional[dict[str, str]] = None,
    timeout: float = 10.0,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> httpx.Response:
    """
    POSTs a JSON body and returns the response (any status code).

    Drop-in replacement for requests_async.post(url, json=..., headers=..., timeout=...).
    Raises one of HTTP_ERRORS if the request could not be completed. `transport` exists
    so tests can use httpx.MockTransport.
    """
    async with httpx.AsyncClient(timeout=timeout, transport=transport) as client:
        return await client.post(url, json=json, headers=headers)
