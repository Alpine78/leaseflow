from __future__ import annotations

import importlib
from dataclasses import dataclass
from datetime import date
from uuid import UUID

import pytest

from app.auth import AuthError


def _reminders_module():
    return importlib.import_module("app.routes.lease_reminders")


@dataclass(slots=True)
class _ReminderCandidate:
    lease_id: UUID
    tenant_id: str
    property_id: UUID
    resident_name: str
    rent_due_day_of_month: int
    due_date: date
    days_until_due: int


class _FakeDb:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def list_due_lease_reminders(
        self,
        tenant_id: str,
        as_of_date: date,
        days: int,
    ) -> list[_ReminderCandidate]:
        self.calls.append(
            {
                "tenant_id": tenant_id,
                "as_of_date": as_of_date,
                "days": days,
            }
        )
        return [
            _ReminderCandidate(
                lease_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                tenant_id=tenant_id,
                property_id=UUID("11111111-1111-1111-1111-111111111111"),
                resident_name="Alice Example",
                rent_due_day_of_month=5,
                due_date=date(2026, 4, 5),
                days_until_due=2,
            )
        ]


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


def test_list_due_lease_reminders_uses_auth_tenant_and_default_days(monkeypatch) -> None:
    reminders = _reminders_module()
    db = _FakeDb()
    event = _event_with_auth(tenant_id="tenant-auth", user_id="user-auth")
    event["queryStringParameters"] = {"tenant_id": "tenant-body-should-be-ignored"}
    monkeypatch.setattr(reminders, "_today", lambda: date(2026, 4, 3))

    payload = reminders.list_due_lease_reminders(event, db)

    assert db.calls == [
        {
            "tenant_id": "tenant-auth",
            "as_of_date": date(2026, 4, 3),
            "days": 7,
        }
    ]
    assert payload == {
        "items": [
            {
                "lease_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "tenant_id": "tenant-auth",
                "property_id": "11111111-1111-1111-1111-111111111111",
                "resident_name": "Alice Example",
                "rent_due_day_of_month": 5,
                "due_date": "2026-04-05",
                "days_until_due": 2,
            }
        ]
    }


def test_list_due_lease_reminders_supports_days_query_parameter(monkeypatch) -> None:
    reminders = _reminders_module()
    db = _FakeDb()
    event = _event_with_auth()
    event["queryStringParameters"] = {"days": "14"}
    monkeypatch.setattr(reminders, "_today", lambda: date(2026, 4, 3))

    reminders.list_due_lease_reminders(event, db)

    assert db.calls[0]["days"] == 14


def test_list_due_lease_reminders_rejects_invalid_days(monkeypatch) -> None:
    reminders = _reminders_module()
    db = _FakeDb()
    event = _event_with_auth()
    event["queryStringParameters"] = {"days": "0"}
    monkeypatch.setattr(reminders, "_today", lambda: date(2026, 4, 3))

    with pytest.raises(
        ValueError,
        match="Query parameter 'days' must be an integer between 1 and 31.",
    ):
        reminders.list_due_lease_reminders(event, db)

    assert db.calls == []


def test_list_due_lease_reminders_requires_jwt_claims() -> None:
    reminders = _reminders_module()
    db = _FakeDb()

    with pytest.raises(AuthError, match="Missing JWT claims."):
        reminders.list_due_lease_reminders({}, db)
