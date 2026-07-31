"""
Overdue item email reminder service.
Checks daily for overdue borrowed items and dispatches automated reminder emails.
"""

import asyncio
import logging
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Sequence, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.backend_constants import (
    FROM_EMAIL,
    OVERDUE_AFTER_DAYS,
    REMINDER_HOUR,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
    TIMEOUT,
)
from backend.backend_types import Status
from backend.requests import get_item, request_borrowed_items
from backend.api_security import rotate_api_keys

# --- Logger & Scheduler State ---
# Global logger for recording reminder service execution
logger = logging.getLogger(__name__)

# Global background task scheduler instance
scheduler = AsyncIOScheduler()


# --- Scheduler Initialization ---
def start_email_scheduler() -> AsyncIOScheduler:
    """
    Initializes and starts the background daily scheduler for overdue reminder emails.
    """
    if not scheduler.running:
        trigger = CronTrigger(hour=REMINDER_HOUR, minute=0)
        scheduler.add_job(
            send_overdue_reminders,
            trigger=trigger,
            id="daily_overdue_reminders",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler started: daily overdue reminder job scheduled for %02d:00.", REMINDER_HOUR)
    return scheduler


# --- Overdue Reminder Dispatcher ---
async def send_overdue_reminders() -> None:
    """
    Fetches currently borrowed items from the backend and dispatches emails for overdue items.
    """
    try:
        # Rotate API security key before communicating with database
        logger.info("[REMINDER] Rotating API keys before requesting borrowed items.")
        rotate_api_keys()
        
        # Request borrowed items list from backend
        items = await request_borrowed_items()
    except Exception as e:
        logger.error("[REMINDER] Failed to fetch borrowed items: %s", e)
        return

    if not items:
        logger.info("[REMINDER] No borrowed items returned.")
        return

    now = datetime.now()
    cutoff = timedelta(days=OVERDUE_AFTER_DAYS)

    # Standardize items structure (handles tuple of 3 lists or list of record tuples)
    records: list[tuple[Any, ...]] = []
    if isinstance(items, tuple) and len(items) == 3:
        time_borrowed, statuses, item_ids = items
        for borrowed_at, status, item_id in zip(time_borrowed, statuses, item_ids):
            records.append(("", "", "", item_id, borrowed_at, status))
    elif isinstance(items, list):
        records = items

    overdue_records: list[tuple[str, str, str, datetime]] = []
    
    # Process each record and identify overdue items
    for item_tuple in records:
        if len(item_tuple) == 6:
            user_id, name, email, item_id, borrowed_at, status = item_tuple
        elif len(item_tuple) == 3:
            user_id, name, email = "", "", ""
            borrowed_at, status, item_id = item_tuple
        else:
            continue

        # Check if item checkout duration exceeds the overdue threshold
        if status == Status.BORROWED and (now - borrowed_at) > cutoff:
            item_name, _ = await get_item(item_id)
            if not item_name:
                item_name = f"Item {item_id}"
            overdue_records.append((name, email, item_name, borrowed_at))

    if not overdue_records:
        logger.info("[REMINDER] No overdue items today.")
        return

    logger.info("[REMINDER] %d overdue item(s) found - sending reminders.", len(overdue_records))
    
    # Offload blocking SMTP email transmission to background thread
    await asyncio.to_thread(_send_batch_reminder_emails, overdue_records)


# --- SMTP Email Batch Processor ---
def _send_batch_reminder_emails(
    overdue_records: Sequence[tuple[str, str, str, datetime]]
) -> None:
    """
    Sends email notifications over a single SMTP connection for all overdue records.
    """
    # Filter records containing a valid target recipient email address
    valid_records = [rec for rec in overdue_records if rec[1]]
    skipped_count = len(overdue_records) - len(valid_records)
    if skipped_count > 0:
        logger.warning("[REMINDER] Skipped %d record(s) missing email addresses.", skipped_count)

    if not valid_records:
        return

    try:
        # Connect to SMTP mail server using TLS encryption
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=TIMEOUT) as server:
            server.starttls()
            if SMTP_USERNAME:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)

            # Iterate over recipients and transmit reminder email messages
            for name, email, item_name, borrowed_at in valid_records:
                days_out = (datetime.now() - borrowed_at).days
                message = EmailMessage()
                message["Subject"] = f"Reminder: '{item_name}' is overdue"
                message["From"] = FROM_EMAIL
                message["To"] = email
                message.set_content(
                    f"Hi {name or 'there'},\n\n"
                    f"Our records show '{item_name}' has been checked out since "
                    f"{borrowed_at.strftime('%b %d, %Y')} ({days_out} days ago) and hasn't "
                    f"been returned yet. Please return it at your earliest convenience.\n\n"
                    f"This is an automated reminder and will be sent again each morning "
                    f"until the item is returned."
                )
                try:
                    server.send_message(message)
                    logger.info("[REMINDER] Sent overdue reminder to %s for '%s'.", email, item_name)
                except Exception as send_err:
                    logger.error("[REMINDER] Failed to email %s about '%s': %s", email, item_name, send_err)
    except Exception as connection_err:
        logger.error("[REMINDER] SMTP session error: %s", connection_err)

