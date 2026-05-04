from __future__ import annotations

import importlib
from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace
from uuid import UUID


def _delivery_module():
    return importlib.import_module("app.routes.notification_email_delivery")


@dataclass(slots=True)
class _PreparationResult:
    tenant_id: str | None
    candidate_count: int
    created_count: int
    duplicate_count: int


@dataclass(slots=True)
class _DeliveryRecord:
    delivery_id: UUID
    tenant_id: str
    notification_id: UUID
    contact_id: UUID
    recipient_email: str
    subject: str
    body: str
    due_date: date
    attempt_count: int
    last_error_code: str | None


class _FakeDb:
    def __init__(self, deliveries: list[_DeliveryRecord] | None = None) -> None:
        self.deliveries = deliveries or []
        self.prepare_calls: list[str | None] = []
        self.list_calls: list[tuple[str | None, int, int]] = []
        self.sent_calls: list[tuple[str, UUID]] = []
        self.failed_calls: list[tuple[str, UUID, str]] = []

    def create_missing_notification_email_deliveries(
        self,
        tenant_id: str | None,
    ) -> _PreparationResult:
        self.prepare_calls.append(tenant_id)
        return _PreparationResult(
            tenant_id=tenant_id,
            candidate_count=len(self.deliveries),
            created_count=len(self.deliveries),
            duplicate_count=0,
        )

    def list_pending_notification_email_deliveries(
        self,
        tenant_id: str | None,
        max_attempts: int,
        limit: int,
    ) -> list[_DeliveryRecord]:
        self.list_calls.append((tenant_id, max_attempts, limit))
        return self.deliveries[:limit]

    def mark_notification_email_delivery_sent(
        self,
        tenant_id: str,
        delivery_id: UUID,
    ) -> None:
        self.sent_calls.append((tenant_id, delivery_id))

    def mark_notification_email_delivery_failed(
        self,
        tenant_id: str,
        delivery_id: UUID,
        error_code: str,
    ) -> None:
        self.failed_calls.append((tenant_id, delivery_id, error_code))


class _FakeSender:
    def __init__(self, *, fail_code: str | None = None) -> None:
        self.fail_code = fail_code
        self.sent: list[tuple[str, str, str, str]] = []

    def send(
        self,
        *,
        sender_email: str,
        recipient_email: str,
        subject: str,
        body: str,
    ) -> None:
        if self.fail_code:
            delivery = _delivery_module()
            raise delivery.NotificationEmailSendError(self.fail_code)
        self.sent.append((sender_email, recipient_email, subject, body))


def _settings(**overrides: object) -> SimpleNamespace:
    values = {
        "notification_email_delivery_enabled": True,
        "notification_email_sender": "sender@example.test",
        "notification_email_batch_size": 25,
        "notification_email_max_attempts": 3,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _event(*, tenant_id: str | None = "tenant-auth") -> dict:
    detail = {}
    if tenant_id is not None:
        detail["tenant_id"] = tenant_id
    return {
        "source": "leaseflow.internal",
        "detail-type": "deliver_notification_emails",
        "detail": detail,
    }


def _delivery_record() -> _DeliveryRecord:
    return _DeliveryRecord(
        delivery_id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
        tenant_id="tenant-auth",
        notification_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        contact_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        recipient_email="recipient@example.test",
        subject="Rent due soon",
        body="Rent is due in 2 days.",
        due_date=date(2026, 4, 9),
        attempt_count=0,
        last_error_code=None,
    )


def test_deliver_notification_emails_disabled_does_not_prepare_or_send() -> None:
    delivery = _delivery_module()
    db = _FakeDb([_delivery_record()])
    sender = _FakeSender()

    payload = delivery.deliver_notification_emails(
        _event(),
        db,
        _settings(notification_email_delivery_enabled=False),
        sender=sender,
    )

    assert payload == {
        "enabled": False,
        "tenant_id": "tenant-auth",
        "candidate_count": 0,
        "created_count": 0,
        "duplicate_count": 0,
        "attempted_count": 0,
        "sent_count": 0,
        "failed_count": 0,
    }
    assert db.prepare_calls == []
    assert sender.sent == []


def test_deliver_notification_emails_sends_pending_delivery_and_marks_success() -> None:
    delivery = _delivery_module()
    record = _delivery_record()
    db = _FakeDb([record])
    sender = _FakeSender()

    payload = delivery.deliver_notification_emails(
        _event(),
        db,
        _settings(),
        sender=sender,
    )

    assert db.prepare_calls == ["tenant-auth"]
    assert db.list_calls == [("tenant-auth", 3, 25)]
    assert sender.sent == [
        (
            "sender@example.test",
            "recipient@example.test",
            "Rent due soon",
            "Rent is due in 2 days.",
        )
    ]
    assert db.sent_calls == [("tenant-auth", record.delivery_id)]
    assert db.failed_calls == []
    assert payload == {
        "enabled": True,
        "tenant_id": "tenant-auth",
        "candidate_count": 1,
        "created_count": 1,
        "duplicate_count": 0,
        "attempted_count": 1,
        "sent_count": 1,
        "failed_count": 0,
    }


def test_deliver_notification_emails_marks_sanitized_failure_without_leaking_payload() -> None:
    delivery = _delivery_module()
    record = _delivery_record()
    db = _FakeDb([record])
    sender = _FakeSender(fail_code="smtp_auth_failed")

    payload = delivery.deliver_notification_emails(
        _event(),
        db,
        _settings(),
        sender=sender,
    )

    assert db.sent_calls == []
    assert db.failed_calls == [("tenant-auth", record.delivery_id, "smtp_auth_failed")]
    assert payload == {
        "enabled": True,
        "tenant_id": "tenant-auth",
        "candidate_count": 1,
        "created_count": 1,
        "duplicate_count": 0,
        "attempted_count": 1,
        "sent_count": 0,
        "failed_count": 1,
    }
    assert "recipient@example.test" not in str(payload)


def test_deliver_notification_emails_defaults_to_all_tenants_when_tenant_missing() -> None:
    delivery = _delivery_module()
    record = _delivery_record()
    db = _FakeDb([record])

    payload = delivery.deliver_notification_emails(
        _event(tenant_id=None),
        db,
        _settings(),
        sender=_FakeSender(),
    )

    assert db.prepare_calls == [None]
    assert db.list_calls == [(None, 3, 25)]
    assert payload["tenant_id"] is None
