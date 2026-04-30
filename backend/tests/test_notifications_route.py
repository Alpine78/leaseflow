from __future__ import annotations

import importlib
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from app.auth import AuthError


def _notifications_module():
    return importlib.import_module("app.routes.notifications")


@dataclass(slots=True)
class _NotificationRecord:
    notification_id: UUID
    tenant_id: str
    lease_id: UUID
    type: str
    title: str
    message: str
    due_date: date
    created_at: datetime
    read_at: datetime | None


class _FakeDb:
    def __init__(self) -> None:
        self.list_calls: list[str] = []
        self.read_calls: list[tuple[str, UUID]] = []

    def list_notifications(self, tenant_id: str) -> list[_NotificationRecord]:
        self.list_calls.append(tenant_id)
        return [
            _NotificationRecord(
                notification_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                tenant_id=tenant_id,
                lease_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                type="rent_due_soon",
                title="Rent due soon",
                message="Rent is due in 2 days.",
                due_date=date(2026, 4, 9),
                created_at=datetime(2026, 4, 7, tzinfo=UTC),
                read_at=None,
            )
        ]

    def mark_notification_read(
        self,
        tenant_id: str,
        notification_id: UUID,
    ) -> _NotificationRecord:
        self.read_calls.append((tenant_id, notification_id))
        return _NotificationRecord(
            notification_id=notification_id,
            tenant_id=tenant_id,
            lease_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            type="rent_due_soon",
            title="Rent due soon",
            message="Rent is due in 2 days.",
            due_date=date(2026, 4, 9),
            created_at=datetime(2026, 4, 7, tzinfo=UTC),
            read_at=datetime(2026, 4, 8, 10, 30, tzinfo=UTC),
        )


def _event_with_auth(*, tenant_id: str = "tenant-from-token", user_id: str = "user-123") -> dict:
    return {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": user_id,
                        "custom:tenant_id": tenant_id,
                    }
                }
            }
        }
    }


def test_list_notifications_uses_auth_tenant_not_client_input() -> None:
    notifications = _notifications_module()
    db = _FakeDb()
    event = _event_with_auth(tenant_id="tenant-auth", user_id="user-auth")
    event["queryStringParameters"] = {"tenant_id": "tenant-from-client-should-be-ignored"}

    payload = notifications.list_notifications(event, db)

    assert db.list_calls == ["tenant-auth"]
    assert payload == {
        "items": [
            {
                "notification_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "tenant_id": "tenant-auth",
                "lease_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "type": "rent_due_soon",
                "title": "Rent due soon",
                "message": "Rent is due in 2 days.",
                "due_date": "2026-04-09",
                "created_at": "2026-04-07T00:00:00+00:00",
                "read_at": None,
            }
        ]
    }


def test_list_notifications_requires_jwt_claims() -> None:
    notifications = _notifications_module()
    db = _FakeDb()

    with pytest.raises(AuthError, match="Missing JWT claims."):
        notifications.list_notifications({}, db)


def test_mark_notification_read_uses_auth_tenant_and_returns_updated_record() -> None:
    notifications = _notifications_module()
    db = _FakeDb()
    notification_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    event = _event_with_auth(tenant_id="tenant-auth", user_id="user-auth")
    event["queryStringParameters"] = {"tenant_id": "tenant-from-client-should-be-ignored"}
    event["body"] = '{"tenant_id":"tenant-from-body-should-be-ignored"}'

    payload = notifications.mark_notification_read(event, db, notification_id)

    assert db.read_calls == [("tenant-auth", notification_id)]
    assert payload == {
        "notification_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "tenant_id": "tenant-auth",
        "lease_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "type": "rent_due_soon",
        "title": "Rent due soon",
        "message": "Rent is due in 2 days.",
        "due_date": "2026-04-09",
        "created_at": "2026-04-07T00:00:00+00:00",
        "read_at": "2026-04-08T10:30:00+00:00",
    }


def test_mark_notification_read_requires_jwt_claims() -> None:
    notifications = _notifications_module()
    db = _FakeDb()

    with pytest.raises(AuthError, match="Missing JWT claims."):
        notifications.mark_notification_read(
            {},
            db,
            UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        )
