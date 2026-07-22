"""
Global state for the backend application.
"""
import asyncio

# Maps the unique request identifiers to their respective asynchronous placeholders to wait for incoming data
pending_requests: dict[str, asyncio.Future] = {}
