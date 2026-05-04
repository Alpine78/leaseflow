from __future__ import annotations

import smtplib

import pytest

from app.email_delivery import NotificationEmailSendError, SmtpNotificationEmailSender


class _FakeSmtp:
    def __init__(self) -> None:
        self.started_tls = False
        self.login_calls: list[tuple[str, str]] = []
        self.sendmail_calls: list[tuple[str, list[str], str]] = []

    def __enter__(self) -> _FakeSmtp:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.login_calls.append((username, password))

    def sendmail(self, sender: str, recipients: list[str], message: str) -> None:
        self.sendmail_calls.append((sender, recipients, message))


def test_smtp_sender_uses_starttls_login_and_sends_email_message() -> None:
    smtp = _FakeSmtp()
    factory_calls: list[tuple[str, int, int]] = []

    def factory(host: str, port: int, timeout: int) -> _FakeSmtp:
        factory_calls.append((host, port, timeout))
        return smtp

    sender = SmtpNotificationEmailSender(
        host="smtp.example.test",
        port=587,
        username="smtp-user",
        password="smtp-password",
        smtp_factory=factory,
    )

    sender.send(
        sender_email="sender@example.test",
        recipient_email="recipient@example.test",
        subject="Rent due soon",
        body="Rent is due in 2 days.",
    )

    assert factory_calls == [("smtp.example.test", 587, 10)]
    assert smtp.started_tls is True
    assert smtp.login_calls == [("smtp-user", "smtp-password")]
    assert len(smtp.sendmail_calls) == 1
    assert smtp.sendmail_calls[0][0] == "sender@example.test"
    assert smtp.sendmail_calls[0][1] == ["recipient@example.test"]
    assert "Subject: Rent due soon" in smtp.sendmail_calls[0][2]
    assert "Rent is due in 2 days." in smtp.sendmail_calls[0][2]


def test_smtp_sender_maps_authentication_error_to_sanitized_code() -> None:
    class _AuthFailingSmtp(_FakeSmtp):
        def login(self, username: str, password: str) -> None:
            raise smtplib.SMTPAuthenticationError(535, b"authentication failed")

    sender = SmtpNotificationEmailSender(
        host="smtp.example.test",
        port=587,
        username="smtp-user",
        password="smtp-password",
        smtp_factory=lambda host, port, timeout: _AuthFailingSmtp(),
    )

    with pytest.raises(NotificationEmailSendError) as exc_info:
        sender.send(
            sender_email="sender@example.test",
            recipient_email="recipient@example.test",
            subject="Rent due soon",
            body="Rent is due in 2 days.",
        )

    assert exc_info.value.code == "smtp_auth_failed"
