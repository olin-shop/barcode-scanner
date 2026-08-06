"""
Global state for the backend application.
"""

import asyncio
import logging
import os
from datetime import datetime

import pandas as pd

from backend.backend_constants import DAY_IN_SECONDS
from pathlib import Path

logger = logging.getLogger(__name__)

# Maps the unique request identifiers to their respective
# asynchronous placeholders to wait for incoming data
pending_requests: dict[str, asyncio.Future] = {}

# Caches the pandas DataFrames for the intro and 303 sheets
# along with a timestamp of when they were retrieved
sheet_cache: dict[str, dict] = {
    "intro": {"data": None, "timestamp": None},
    "303": {"data": None, "timestamp": None},
}

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"

def save_cache_to_disk() -> None:
    """
    Saves the current sheet DataFrames to CSV files on disk.
    """
    try:
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
        
        for key in ["intro", "303"]:
            data = sheet_cache[key]["data"]
            if data is not None and isinstance(data, pd.DataFrame):
                path = os.path.join(CACHE_DIR, f"{key}_sheet.csv")
                data.to_csv(path, index=False)
                logger.info("Saved %s sheet cache to %s", key, path)
    except Exception as e:
        logger.error("Failed to save sheet cache to disk: %s", e)

def load_cache_from_disk() -> None:
    """
    Loads sheet DataFrames from local CSV files if they are newer than 24 hours.
    """
    try:
        now = datetime.now()
        for key in ["intro", "303"]:
            path = os.path.join(CACHE_DIR, f"{key}_sheet.csv")
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                file_time = datetime.fromtimestamp(mtime)
                
                if (now - file_time).total_seconds() < DAY_IN_SECONDS:
                    df = pd.read_csv(path)
                    sheet_cache[key]["data"] = df
                    sheet_cache[key]["timestamp"] = file_time
                    logger.info("Loaded %s sheet cache from %s", key, path)
                else:
                    logger.info("Cache file %s is older than 24 hours, ignoring.", path)
    except Exception as e:
        logger.error("Failed to load sheet cache from disk: %s", e)
