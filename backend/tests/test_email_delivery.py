from __future__ import annotations

from email.parser import Parser

from app.email_delivery import SmtpNotificationEmailSender


class _FakeSmtp:
    sent_messages: list[str] = []

    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self) -> _FakeSmtp:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def starttls(self) -> None:
        return None

    def login(self, username: str, password: str) -> None:
        return None

    def sendmail(self, sender: str, recipients: list[str], message: str) -> None:
        self.sent_messages.append(message)


def test_smtp_sender_adds_ses_message_tag_and_configuration_set_header() -> None:
    _FakeSmtp.sent_messages = []
    sender = SmtpNotificationEmailSender(
        host="smtp.example.test",
        port=587,
        username="smtp-user",
        password="smtp-password",
        smtp_factory=_FakeSmtp,
    )

    sender.send(
        sender_email="sender@example.test",
        recipient_email="recipient@example.test",
        subject="Rent due soon",
        body="Rent is due in 2 days.",
        event_correlation_token="11111111-1111-4111-8111-111111111111",
        configuration_set="leaseflow-dev-events",
    )

    message = Parser().parsestr(_FakeSmtp.sent_messages[0])

    assert (
        message["X-SES-MESSAGE-TAGS"]
        == "leaseflow_delivery_correlation=11111111-1111-4111-8111-111111111111"
    )
    assert message["X-SES-CONFIGURATION-SET"] == "leaseflow-dev-events"


def test_smtp_sender_omits_configuration_set_header_when_not_configured() -> None:
    _FakeSmtp.sent_messages = []
    sender = SmtpNotificationEmailSender(
        host="smtp.example.test",
        port=587,
        username="smtp-user",
        password="smtp-password",
        smtp_factory=_FakeSmtp,
    )

    sender.send(
        sender_email="sender@example.test",
        recipient_email="recipient@example.test",
        subject="Rent due soon",
        body="Rent is due in 2 days.",
        event_correlation_token="11111111-1111-4111-8111-111111111111",
        configuration_set="",
    )

    message = Parser().parsestr(_FakeSmtp.sent_messages[0])

    assert (
        message["X-SES-MESSAGE-TAGS"]
        == "leaseflow_delivery_correlation=11111111-1111-4111-8111-111111111111"
    )
    assert "X-SES-CONFIGURATION-SET" not in message
