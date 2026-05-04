from __future__ import annotations

import smtplib
from collections.abc import Callable
from email.message import EmailMessage


class NotificationEmailSendError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SmtpNotificationEmailSender:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        smtp_factory: Callable[[str, int, int], smtplib.SMTP] = smtplib.SMTP,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._smtp_factory = smtp_factory

    def send(
        self,
        *,
        sender_email: str,
        recipient_email: str,
        subject: str,
        body: str,
    ) -> None:
        message = EmailMessage()
        message["From"] = sender_email
        message["To"] = recipient_email
        message["Subject"] = subject
        message.set_content(body)

        try:
            with self._smtp_factory(self._host, self._port, 10) as smtp:
                smtp.starttls()
                smtp.login(self._username, self._password)
                smtp.sendmail(sender_email, [recipient_email], message.as_string())
        except smtplib.SMTPAuthenticationError as exc:
            raise NotificationEmailSendError("smtp_auth_failed") from exc
        except smtplib.SMTPRecipientsRefused as exc:
            raise NotificationEmailSendError("smtp_recipient_refused") from exc
        except smtplib.SMTPSenderRefused as exc:
            raise NotificationEmailSendError("smtp_sender_refused") from exc
        except smtplib.SMTPResponseException as exc:
            raise NotificationEmailSendError("smtp_response_error") from exc
        except OSError as exc:
            raise NotificationEmailSendError("smtp_network_error") from exc
        except smtplib.SMTPException as exc:
            raise NotificationEmailSendError("smtp_error") from exc
