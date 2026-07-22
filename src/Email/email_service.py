"""
Overdue item email reminder service.
Checks daily for overdue borrowed items and dispatches automated reminder emails.
"""

import asyncio
import logging
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Sequence

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

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


def start_email_scheduler() -> AsyncIOScheduler:
    """
    Initializes and starts the APScheduler AsyncIOScheduler to run
    `send_overdue_reminders` daily at REMINDER_HOUR.
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


async def send_overdue_reminders() -> None:
    """
    Fetches the current borrowed-items list and emails a reminder to
    every borrower whose item is overdue.
    """
    try:
        items = await request_borrowed_items()
    except Exception as e:
        logger.error("[REMINDER] Failed to fetch borrowed items: %s", e)
        return

    now = datetime.now()
    cutoff = timedelta(days=OVERDUE_AFTER_DAYS)

    overdue_records: list[tuple[str, str, str, datetime]] = []
    for user_id, name, email, item_id, borrowed_at, status in items:
        if status == Status.BORROWED and (now - borrowed_at) > cutoff:
            item_name, _ = await get_item(item_id)
            if not item_name:
                item_name = f"Item {item_id}"
            overdue_records.append((name, email, item_name, borrowed_at))

    if not overdue_records:
        logger.info("[REMINDER] No overdue items today.")
        return

    logger.info("[REMINDER] %d overdue item(s) found - sending reminders.", len(overdue_records))
    
    # Offload blocking SMTP batch execution to a thread
    await asyncio.to_thread(_send_batch_reminder_emails, overdue_records)


def _send_batch_reminder_emails(
    overdue_records: Sequence[tuple[str, str, str, datetime]]
) -> None:
    """
    Opens a single SMTP context manager connection, loops through overdue users
    to send all emails, and lets the context manager close the connection at the end.
    """
    valid_records = [rec for rec in overdue_records if rec[1]]
    skipped_count = len(overdue_records) - len(valid_records)
    if skipped_count > 0:
        logger.warning("[REMINDER] Skipped %d record(s) missing email addresses.", skipped_count)

    if not valid_records:
        return

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=TIMEOUT) as server:
            server.starttls()
            if SMTP_USERNAME:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)

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
