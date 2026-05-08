from __future__ import annotations

from typing import Any, Protocol

from app.config import ConfigError, Settings
from app.db import Database
from app.email_delivery import NotificationEmailSendError, SmtpNotificationEmailSender
from app.metrics import emit_emf_metrics

_METRIC_NAMESPACE = "LeaseFlow/NotificationEmailDelivery"
_METRIC_SERVICE = "backend"
_METRIC_OPERATION = "deliver_notification_emails"


class NotificationEmailSender(Protocol):
    def send(
        self,
        *,
        sender_email: str,
        recipient_email: str,
        subject: str,
        body: str,
        event_correlation_token: str,
        configuration_set: str,
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
        payload = _payload(
            enabled=False,
            tenant_id=tenant_id,
            candidate_count=0,
            created_count=0,
            duplicate_count=0,
            attempted_count=0,
            sent_count=0,
            failed_count=0,
            skipped_count=0,
            retry_exhausted_count=0,
        )
        _emit_delivery_metrics(settings=settings, result="disabled", payload=payload)
        return payload

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
    retry_exhausted_count = 0
    for item in pending:
        try:
            sender.send(
                sender_email=settings.notification_email_sender,
                recipient_email=item.recipient_email,
                subject=item.subject,
                body=item.body,
                event_correlation_token=str(item.event_correlation_token),
                configuration_set=settings.notification_email_configuration_set,
            )
        except NotificationEmailSendError as exc:
            failed_count += 1
            if item.attempt_count + 1 >= settings.notification_email_max_attempts:
                retry_exhausted_count += 1
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

    payload = _payload(
        enabled=True,
        tenant_id=tenant_id,
        candidate_count=preparation.candidate_count,
        created_count=preparation.created_count,
        duplicate_count=preparation.duplicate_count,
        attempted_count=len(pending),
        sent_count=sent_count,
        failed_count=failed_count,
        skipped_count=max(preparation.candidate_count - len(pending), 0),
        retry_exhausted_count=retry_exhausted_count,
    )
    _emit_delivery_metrics(
        settings=settings,
        result="completed_with_failures" if failed_count else "completed",
        payload=payload,
    )
    return payload


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
    skipped_count: int,
    retry_exhausted_count: int,
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
        "skipped_count": skipped_count,
        "retry_exhausted_count": retry_exhausted_count,
    }


def _emit_delivery_metrics(
    *,
    settings: Settings,
    result: str,
    payload: dict[str, Any],
) -> None:
    emit_emf_metrics(
        namespace=_METRIC_NAMESPACE,
        environment=settings.app_env,
        service=_METRIC_SERVICE,
        operation=_METRIC_OPERATION,
        result=result,
        metrics={
            "candidate_count": payload["candidate_count"],
            "created_delivery_count": payload["created_count"],
            "attempted_count": payload["attempted_count"],
            "sent_count": payload["sent_count"],
            "failed_count": payload["failed_count"],
            "skipped_count": payload["skipped_count"],
            "retry_exhausted_count": payload["retry_exhausted_count"],
        },
    )
