"""
Unit tests for Email/email_service.py.
Tests APScheduler initialization, overdue item filtering, and SMTP batch email sending.
"""

import asyncio
from datetime import datetime, timedelta
import smtplib
import pytest
from pytest_mock import MockerFixture

from backend.backend_types import Status
import Email.email_service as es


@pytest.mark.asyncio
async def test_start_email_scheduler(mocker: MockerFixture) -> None:
    """Verifies that start_email_scheduler starts the scheduler and adds the daily job."""
    scheduler = es.scheduler
    if scheduler.running:
        scheduler.shutdown(wait=False)

    started_scheduler = es.start_email_scheduler()
    assert started_scheduler.running is True

    # Verify daily_overdue_reminders job is present
    job = started_scheduler.get_job("daily_overdue_reminders")
    assert job is not None

    # Clean up
    started_scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_send_overdue_reminders_no_overdue(mocker: MockerFixture) -> None:
    """Verifies that no emails are dispatched when no items are overdue."""
    now = datetime.now()
    recent_date = now - timedelta(days=5)
    # Item status BORROWED but recent (5 days ago < OVERDUE_AFTER_DAYS=14)
    fake_items = [
        ("user1", "Alice", "alice@example.com", 101, recent_date, Status.BORROWED),
        ("user2", "Bob", "bob@example.com", 102, recent_date, Status.INSTOCK),
    ]

    mocker.patch("Email.email_service.request_borrowed_items", return_value=fake_items)
    mock_send_batch = mocker.patch("Email.email_service._send_batch_reminder_emails")

    await es.send_overdue_reminders()
    mock_send_batch.assert_not_called()


@pytest.mark.asyncio
async def test_send_overdue_reminders_with_overdue_items(mocker: MockerFixture) -> None:
    """Verifies overdue items (>14 days) are filtered, names resolved, and sent in batch."""
    now = datetime.now()
    overdue_date = now - timedelta(days=20)
    recent_date = now - timedelta(days=2)

    fake_items = [
        ("user1", "Alice", "alice@example.com", 101, overdue_date, Status.BORROWED),
        ("user2", "Bob", "bob@example.com", 102, recent_date, Status.BORROWED),
    ]

    mocker.patch("Email.email_service.request_borrowed_items", return_value=fake_items)
    mocker.patch("Email.email_service.get_item", return_value=("Drill Press", Status.BORROWED))
    mock_send_batch = mocker.patch("Email.email_service._send_batch_reminder_emails")

    await es.send_overdue_reminders()

    mock_send_batch.assert_called_once()
    records = mock_send_batch.call_args[0][0]
    assert len(records) == 1
    assert records[0] == ("Alice", "alice@example.com", "Drill Press", overdue_date)


@pytest.mark.asyncio
async def test_send_overdue_reminders_handles_fetch_exception(mocker: MockerFixture) -> None:
    """Verifies that exceptions during item fetch are handled gracefully."""
    mocker.patch("Email.email_service.request_borrowed_items", side_effect=RuntimeError("Network Error"))
    mock_send_batch = mocker.patch("Email.email_service._send_batch_reminder_emails")

    # Should not crash
    await es.send_overdue_reminders()
    mock_send_batch.assert_not_called()


def test_send_batch_reminder_emails_success(mocker: MockerFixture) -> None:
    """Verifies single SMTP connection context manager batching and email transmission."""
    now = datetime.now() - timedelta(days=20)
    overdue_records = [
        ("Alice", "alice@example.com", "Band Saw", now),
        ("Bob", "bob@example.com", "Laser Cutter", now),
    ]

    mock_smtp_instance = mocker.MagicMock()
    mock_smtp_cls = mocker.patch("smtplib.SMTP", return_value=mock_smtp_instance)
    mock_smtp_instance.__enter__.return_value = mock_smtp_instance

    es._send_batch_reminder_emails(overdue_records)

    # Verify single SMTP connection established
    mock_smtp_cls.assert_called_once_with(es.SMTP_HOST, es.SMTP_PORT, timeout=es.TIMEOUT)
    mock_smtp_instance.starttls.assert_called_once()

    # Verify two emails were sent via send_message
    assert mock_smtp_instance.send_message.call_count == 2


def test_send_batch_reminder_emails_skips_empty_emails(mocker: MockerFixture) -> None:
    """Verifies records without valid email addresses are skipped."""
    now = datetime.now() - timedelta(days=20)
    overdue_records = [
        ("NoEmailUser", "", "Router", now),
    ]

    mock_smtp_cls = mocker.patch("smtplib.SMTP")

    es._send_batch_reminder_emails(overdue_records)

    # Should not even open SMTP connection if no valid records
    mock_smtp_cls.assert_not_called()


def test_send_batch_reminder_emails_resilient_to_single_send_failure(mocker: MockerFixture) -> None:
    """Verifies that failure on one recipient doesn't stop remaining batch emails from sending."""
    now = datetime.now() - timedelta(days=20)
    overdue_records = [
        ("Alice", "alice@example.com", "Band Saw", now),
        ("Bob", "bob@example.com", "Laser Cutter", now),
    ]

    mock_smtp_instance = mocker.MagicMock()
    mocker.patch("smtplib.SMTP", return_value=mock_smtp_instance)
    mock_smtp_instance.__enter__.return_value = mock_smtp_instance

    # First email fails, second succeeds
    mock_smtp_instance.send_message.side_effect = [smtplib.SMTPException("Recipients Refused"), None]

    es._send_batch_reminder_emails(overdue_records)

    assert mock_smtp_instance.send_message.call_count == 2


def test_send_batch_reminder_emails_handles_connection_error(mocker: MockerFixture) -> None:
    """Verifies SMTP connection level failure is caught and logged."""
    now = datetime.now() - timedelta(days=20)
    overdue_records = [("Alice", "alice@example.com", "Band Saw", now)]

    mocker.patch("smtplib.SMTP", side_effect=ConnectionRefusedError("SMTP Server Down"))

    # Should log error and not raise exception
    es._send_batch_reminder_emails(overdue_records)
