"""
Edge case and stress unit tests for Email/email_service.py.
"""

import asyncio
from datetime import datetime, timedelta
import smtplib
import pytest
from pytest_mock import MockerFixture

from backend.backend_types import Status
import Email.email_service as es


def test_send_batch_high_volume_stress(mocker: MockerFixture) -> None:
    """Stress test: verifies single SMTP connection context manager handles 500 records smoothly."""
    now = datetime.now() - timedelta(days=20)
    overdue_records = [
        (f"User_{i}", f"user_{i}@example.com", f"Item_{i}", now)
        for i in range(500)
    ]

    mock_smtp_instance = mocker.MagicMock()
    mock_smtp_cls = mocker.patch("smtplib.SMTP", return_value=mock_smtp_instance)
    mock_smtp_instance.__enter__.return_value = mock_smtp_instance

    es._send_batch_reminder_emails(overdue_records)

    # Verify connection opened once and 500 messages sent
    mock_smtp_cls.assert_called_once()
    assert mock_smtp_instance.send_message.call_count == 500


def test_send_batch_unicode_and_special_emails(mocker: MockerFixture) -> None:
    """Edge case: verifies Unicode names and email addresses with tags/special characters."""
    now = datetime.now() - timedelta(days=20)
    overdue_records = [
        ("José Ramírez", "jose+tag@olin.edu", "CNC Mill", now),
        ("Aña & François", "francois.o'reilly@domain.org", "3D Printer", now),
    ]

    mock_smtp_instance = mocker.MagicMock()
    mocker.patch("smtplib.SMTP", return_value=mock_smtp_instance)
    mock_smtp_instance.__enter__.return_value = mock_smtp_instance

    es._send_batch_reminder_emails(overdue_records)

    assert mock_smtp_instance.send_message.call_count == 2


def test_send_batch_mid_stream_disconnection(mocker: MockerFixture) -> None:
    """Edge case: server drops connection mid-stream after sending first message."""
    now = datetime.now() - timedelta(days=20)
    overdue_records = [
        ("User 1", "user1@example.com", "Item 1", now),
        ("User 2", "user2@example.com", "Item 2", now),
    ]

    mock_smtp_instance = mocker.MagicMock()
    mocker.patch("smtplib.SMTP", return_value=mock_smtp_instance)
    mock_smtp_instance.__enter__.return_value = mock_smtp_instance

    # First send succeeds, second raises SMTPServerDisconnected
    mock_smtp_instance.send_message.side_effect = [None, smtplib.SMTPServerDisconnected("Connection Reset")]

    # Should not raise exception
    es._send_batch_reminder_emails(overdue_records)


@pytest.mark.asyncio
async def test_overdue_threshold_boundary_math(mocker: MockerFixture) -> None:
    """Boundary test: items exactly 14 days ago vs 13.99 days vs 1000 days ago."""
    now = datetime.now()
    exact_14_days = now - timedelta(days=14, seconds=5)      # Just past cutoff -> overdue
    just_under_14 = now - timedelta(days=13, hours=23)       # Not overdue
    very_old = now - timedelta(days=1000)                      # Overdue

    fake_items = [
        ("u1", "Alice", "alice@example.com", 1, exact_14_days, Status.BORROWED),
        ("u2", "Bob", "bob@example.com", 2, just_under_14, Status.BORROWED),
        ("u3", "Charlie", "charlie@example.com", 3, very_old, Status.BORROWED),
    ]

    mocker.patch("Email.email_service.request_borrowed_items", return_value=fake_items)
    mocker.patch("Email.email_service.get_item", side_effect=lambda item_id: (f"Item {item_id}", Status.BORROWED))
    mock_send_batch = mocker.patch("Email.email_service._send_batch_reminder_emails")

    await es.send_overdue_reminders()

    mock_send_batch.assert_called_once()
    records = mock_send_batch.call_args[0][0]
    # u1 (exact_14_days) and u3 (very_old) should be sent; u2 (just_under_14) ignored
    assert len(records) == 2
    names = [r[0] for r in records]
    assert "Alice" in names
    assert "Charlie" in names
    assert "Bob" not in names


@pytest.mark.asyncio
async def test_concurrent_send_overdue_reminders(mocker: MockerFixture) -> None:
    """Stress test: concurrent invocation of send_overdue_reminders does not collide."""
    now = datetime.now() - timedelta(days=20)
    fake_items = [("u1", "Alice", "alice@example.com", 1, now, Status.BORROWED)]

    mocker.patch("Email.email_service.request_borrowed_items", return_value=fake_items)
    mocker.patch("Email.email_service.get_item", return_value=("Drill", Status.BORROWED))
    mock_send_batch = mocker.patch("Email.email_service._send_batch_reminder_emails")

    # Run 3 reminder calls concurrently
    await asyncio.gather(
        es.send_overdue_reminders(),
        es.send_overdue_reminders(),
        es.send_overdue_reminders(),
    )

    assert mock_send_batch.call_count == 3
