"""
MediaMitigator — Notification helpers (toast + optional email).

Author: Nathan
"""

import logging
import smtplib
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger(__name__)


def send_toast(title: str, message: str) -> None:
    """Send a Windows toast notification via plyer.

    Args:
        title: Notification title.
        message: Notification body text.
    """
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="MediaMitigator",
            timeout=8,
        )
    except Exception as exc:
        logger.warning("Toast notification failed: %s", exc)


def send_email(settings: dict[str, Any], subject: str, body: str) -> bool:
    """Send an email notification using the configured SMTP settings.

    Args:
        settings: Settings dict containing email_host, email_port,
            email_sender, email_recipient, and email_password keys.
        subject: Email subject line.
        body: Plain-text email body.

    Returns:
        ``True`` if the email was sent, ``False`` otherwise.
    """
    host = settings.get("email_host", "")
    port = int(settings.get("email_port", 587))
    sender = settings.get("email_sender", "")
    recipient = settings.get("email_recipient", "")
    password = settings.get("email_password", "")

    if not all([host, sender, recipient]):
        logger.warning("Email notification skipped — incomplete SMTP config.")
        return False

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            if password:
                server.login(sender, password)
            server.sendmail(sender, [recipient], msg.as_string())
        return True
    except Exception as exc:
        logger.error("Email send failed: %s", exc)
        return False


def notify(
    settings: dict[str, Any],
    title: str,
    message: str,
    email_subject: str | None = None,
) -> None:
    """Send both toast and optional email notifications based on user settings.

    Args:
        settings: User settings dict.
        title: Toast notification title / email fallback subject.
        message: Notification body.
        email_subject: Optional custom email subject; defaults to *title*.
    """
    if settings.get("toast_notifications", False):
        send_toast(title, message)

    if settings.get("email_notifications", False):
        send_email(settings, email_subject or title, message)
