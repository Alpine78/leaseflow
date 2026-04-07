from __future__ import annotations

import importlib
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from app.auth import AuthError


def _leases_module():
    return importlib.import_module("app.routes.leases")


@dataclass(slots=True)
class _LeaseRecord:
    lease_id: UUID
    tenant_id: str
    property_id: UUID
    resident_name: str
    rent_due_day_of_month: int
    start_date: date
    end_date: date
    created_at: datetime


class _FakeDb:
    def __init__(self) -> None:
        self.create_calls: list[dict[str, object]] = []
        self.list_calls: list[str] = []

    def create_lease(
        self,
        tenant_id: str,
        actor_user_id: str,
        property_id: UUID,
        resident_name: str,
        rent_due_day_of_month: int,
        start_date: date,
        end_date: date,
    ) -> _LeaseRecord:
        self.create_calls.append(
            {
                "tenant_id": tenant_id,
                "actor_user_id": actor_user_id,
                "property_id": property_id,
                "resident_name": resident_name,
                "rent_due_day_of_month": rent_due_day_of_month,
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        return _LeaseRecord(
            lease_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            tenant_id=tenant_id,
            property_id=property_id,
            resident_name=resident_name,
            rent_due_day_of_month=5,
            start_date=start_date,
            end_date=end_date,
            created_at=datetime(2026, 4, 7, tzinfo=UTC),
        )

    def list_leases(self, tenant_id: str) -> list[_LeaseRecord]:
        self.list_calls.append(tenant_id)
        return [
            _LeaseRecord(
                lease_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                tenant_id=tenant_id,
                property_id=UUID("11111111-1111-1111-1111-111111111111"),
                resident_name="Alice Example",
                rent_due_day_of_month=5,
                start_date=date(2026, 5, 1),
                end_date=date(2027, 4, 30),
                created_at=datetime(2026, 4, 7, tzinfo=UTC),
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


def _get_leases_event(*, tenant_id: str = "tenant-from-token", user_id: str = "user-123") -> dict:
    event = _event_with_auth(tenant_id=tenant_id, user_id=user_id)
    event["queryStringParameters"] = {"tenant_id": "tenant-from-client-should-be-ignored"}
    return event


def test_list_leases_uses_auth_tenant_not_client_input() -> None:
    leases = _leases_module()
    db = _FakeDb()
    event = _get_leases_event(tenant_id="tenant-auth", user_id="user-auth")

    payload = leases.list_leases(event, db)

    assert db.list_calls == ["tenant-auth"]
    assert payload == {
        "items": [
            {
                "lease_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "tenant_id": "tenant-auth",
                "property_id": "11111111-1111-1111-1111-111111111111",
                "resident_name": "Alice Example",
                "rent_due_day_of_month": 5,
                "start_date": "2026-05-01",
                "end_date": "2027-04-30",
                "created_at": "2026-04-07T00:00:00+00:00",
            }
        ]
    }


def test_list_leases_requires_jwt_claims() -> None:
    leases = _leases_module()
    db = _FakeDb()

    with pytest.raises(AuthError, match="Missing JWT claims."):
        leases.list_leases({}, db)


def test_create_lease_uses_auth_tenant_not_body_tenant() -> None:
    leases = _leases_module()
    db = _FakeDb()
    event = _event_with_auth(tenant_id="tenant-auth", user_id="user-auth")
    property_id = UUID("11111111-1111-1111-1111-111111111111")
    body = {
        "tenant_id": "tenant-body-should-be-ignored",
        "property_id": str(property_id),
        "resident_name": "Alice Example",
        "rent_due_day_of_month": 5,
        "start_date": "2026-05-01",
        "end_date": "2027-04-30",
    }

    payload = leases.create_lease(event, db, body)

    assert db.create_calls == [
        {
            "tenant_id": "tenant-auth",
            "actor_user_id": "user-auth",
            "property_id": property_id,
            "resident_name": "Alice Example",
            "rent_due_day_of_month": 5,
            "start_date": date(2026, 5, 1),
            "end_date": date(2027, 4, 30),
        }
    ]
    assert payload == {
        "lease_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "tenant_id": "tenant-auth",
        "property_id": "11111111-1111-1111-1111-111111111111",
        "resident_name": "Alice Example",
        "rent_due_day_of_month": 5,
        "start_date": "2026-05-01",
        "end_date": "2027-04-30",
        "created_at": "2026-04-07T00:00:00+00:00",
    }


def test_create_lease_requires_all_fields() -> None:
    leases = _leases_module()
    db = _FakeDb()
    event = _event_with_auth()

    with pytest.raises(
        ValueError,
        match=(
            "Fields 'property_id', 'resident_name', "
            "'rent_due_day_of_month', 'start_date', and 'end_date' are required."
        ),
    ):
        leases.create_lease(
            event,
            db,
            {
                "property_id": "11111111-1111-1111-1111-111111111111",
                "resident_name": "Alice Example",
                "start_date": "2026-05-01",
            },
        )

    assert db.create_calls == []


def test_create_lease_rejects_invalid_date_format() -> None:
    leases = _leases_module()
    db = _FakeDb()
    event = _event_with_auth()

    with pytest.raises(ValueError, match="Fields 'start_date' and 'end_date' must use YYYY-MM-DD."):
        leases.create_lease(
            event,
            db,
            {
                "property_id": "11111111-1111-1111-1111-111111111111",
                "resident_name": "Alice Example",
                "rent_due_day_of_month": 5,
                "start_date": "05/01/2026",
                "end_date": "2027-04-30",
            },
        )

    assert db.create_calls == []


def test_create_lease_rejects_end_date_before_start_date() -> None:
    leases = _leases_module()
    db = _FakeDb()
    event = _event_with_auth()

    with pytest.raises(ValueError, match="'end_date' must be on or after 'start_date'."):
        leases.create_lease(
            event,
            db,
            {
                "property_id": "11111111-1111-1111-1111-111111111111",
                "resident_name": "Alice Example",
                "rent_due_day_of_month": 5,
                "start_date": "2027-05-01",
                "end_date": "2027-04-30",
            },
        )

    assert db.create_calls == []


def test_create_lease_rejects_invalid_rent_due_day_of_month() -> None:
    leases = _leases_module()
    db = _FakeDb()
    event = _event_with_auth()

    with pytest.raises(
        ValueError,
        match="Field 'rent_due_day_of_month' must be an integer between 1 and 31.",
    ):
        leases.create_lease(
            event,
            db,
            {
                "property_id": "11111111-1111-1111-1111-111111111111",
                "resident_name": "Alice Example",
                "rent_due_day_of_month": 32,
                "start_date": "2026-05-01",
                "end_date": "2027-04-30",
            },
        )

    assert db.create_calls == []
