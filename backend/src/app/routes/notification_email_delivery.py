from __future__ import annotations

from typing import Any, Protocol

from app.config import ConfigError, Settings
from app.db import Database
from app.email_delivery import NotificationEmailSendError, SmtpNotificationEmailSender


class NotificationEmailSender(Protocol):
    def send(
        self,
        *,
        sender_email: str,
        recipient_email: str,
        subject: str,
        body: str,
    ) -> None: ...


def deliver_notification_emails(
    event: dict[str, Any],
    db: Database,
    settings: Settings,
    sender: NotificationEmailSender | None = None,
) -> dict[str, Any]:
    detail = event.get("detail") or {}
    tenant_id = _parse_tenant_id(detail)

    if not settings.notification_email_delivery_enabled:
        return _payload(
            enabled=False,
            tenant_id=tenant_id,
            candidate_count=0,
            created_count=0,
            duplicate_count=0,
            attempted_count=0,
            sent_count=0,
            failed_count=0,
        )

    if not settings.notification_email_sender.strip():
        raise ConfigError("Set NOTIFICATION_EMAIL_SENDER before enabling email delivery.")

    if sender is None:
        username, password = settings.resolve_notification_email_smtp_credentials()
        sender = SmtpNotificationEmailSender(
            host=settings.notification_email_smtp_host,
            port=settings.notification_email_smtp_port,
            username=username,
            password=password,
        )

    preparation = db.create_missing_notification_email_deliveries(tenant_id=tenant_id)
    pending = db.list_pending_notification_email_deliveries(
        tenant_id=tenant_id,
        max_attempts=settings.notification_email_max_attempts,
        limit=settings.notification_email_batch_size,
    )

    sent_count = 0
    failed_count = 0
    for item in pending:
        try:
            sender.send(
                sender_email=settings.notification_email_sender,
                recipient_email=item.recipient_email,
                subject=item.subject,
                body=item.body,
            )
        except NotificationEmailSendError as exc:
            failed_count += 1
            db.mark_notification_email_delivery_failed(
                tenant_id=item.tenant_id,
                delivery_id=item.delivery_id,
                error_code=exc.code,
            )
        else:
            sent_count += 1
            db.mark_notification_email_delivery_sent(
                tenant_id=item.tenant_id,
                delivery_id=item.delivery_id,
            )

    return _payload(
        enabled=True,
        tenant_id=tenant_id,
        candidate_count=preparation.candidate_count,
        created_count=preparation.created_count,
        duplicate_count=preparation.duplicate_count,
        attempted_count=len(pending),
        sent_count=sent_count,
        failed_count=failed_count,
    )


def _parse_tenant_id(detail: dict[str, Any]) -> str | None:
    tenant_id = str(detail.get("tenant_id", "")).strip()
    return tenant_id or None


def _payload(
    *,
    enabled: bool,
    tenant_id: str | None,
    candidate_count: int,
    created_count: int,
    duplicate_count: int,
    attempted_count: int,
    sent_count: int,
    failed_count: int,
) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "tenant_id": tenant_id,
        "candidate_count": candidate_count,
        "created_count": created_count,
        "duplicate_count": duplicate_count,
        "attempted_count": attempted_count,
        "sent_count": sent_count,
        "failed_count": failed_count,
    }
