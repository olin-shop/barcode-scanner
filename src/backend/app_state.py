"""
Global state for the backend application.
"""
import asyncio

# Maps the unique request identifiers to their respective asynchronous placeholders to wait for incoming data
pending_requests: dict[str, asyncio.Future] = {}

# Caches the pandas DataFrames for the intro and 303 sheets along with a timestamp of when they were retrieved
sheet_cache: dict[str, dict] = {
    "intro": {"data": None, "timestamp": None},
    "303": {"data": None, "timestamp": None}
}
