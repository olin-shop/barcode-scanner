'''
check if borrowed items are late daily, send an automated email to return the item after two weeks. 
Send daily email after that. Email stops being sent once status is no longer overdue.
'''
# imports
import asyncio
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
 
from backend.backend_types import Status
from backend.requests import get_item, request_borrowed_items
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

async def run_daily_overdue_reminder_job() -> None:
    """
    Runs forever: sleeps until the next REMINDER_HOUR (default 8:00 AM
    local time), sends that morning's overdue reminders, then repeats.
 
    Intended to be started once, alongside the server (see
    endpoints.py's before_serving hook).
    """
    while True:
        await asyncio.sleep(_seconds_until_next_run(REMINDER_HOUR))
        try:
            await send_overdue_reminders()
        except Exception as e:
            # A single bad morning shouldn't kill the recurring job.
            print(f"[REMINDER] Unexpected error while sending overdue reminders: {e}")
 
 
async def send_overdue_reminders() -> None:
    """
    Fetches the current borrowed-items list and emails a reminder to
    every borrower whose item is overdue.
    """
    items = await request_borrowed_items()
    now = datetime.now()
    cutoff = timedelta(days=OVERDUE_AFTER_DAYS)
 
    overdue = [
        record
        for record in items
        if record[5] == Status.BORROWED and (now - record[4]) > cutoff
    ]
 
    if not overdue:
        print("[REMINDER] No overdue items today.")
        return
 
    print(f"[REMINDER] {len(overdue)} overdue item(s) found - sending reminders.")
    for user_id, name, email, item_id, borrowed_at, status in overdue:
        item_name, _ = await get_item(item_id)
        if not item_name:
            item_name = f"Item {item_id}"
        await asyncio.to_thread(_send_reminder_email, name, email, item_name, borrowed_at)
 
 
def _seconds_until_next_run(hour: int) -> float:
    """Seconds from now until the next occurrence of `hour`:00 local time."""
    now = datetime.now()
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()
 
 
def _send_reminder_email(name: str, email: str, item_name: str, borrowed_at: datetime) -> None:
    """Sends a single overdue reminder email. Runs in a worker thread since
    smtplib is blocking."""
    if not email:
        print(f"[REMINDER] No email on file for {name!r}; skipping reminder for {item_name!r}.")
        return
 
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
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=TIMEOUT) as server:
            server.starttls()
            if SMTP_USERNAME:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)
        print(f"[REMINDER] Sent overdue reminder to {email} for '{item_name}'.")
    except Exception as e:
        print(f"[REMINDER] Failed to email {email} about '{item_name}': {e}")