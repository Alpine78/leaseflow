from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.auth import AuthError
from app.models import Property
from app.routes.properties import create_property, list_properties


class _FakeDb:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []
        self.list_calls: list[str] = []

    def create_property(
        self,
        tenant_id: str,
        actor_user_id: str,
        name: str,
        address: str,
    ) -> Property:
        self.calls.append(
            {
                "tenant_id": tenant_id,
                "actor_user_id": actor_user_id,
                "name": name,
                "address": address,
            }
        )
        return Property(
            property_id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            address=address,
            created_at=datetime(2026, 3, 12, tzinfo=UTC),
        )

    def list_properties(self, tenant_id: str) -> list[Property]:
        self.list_calls.append(tenant_id)
        return [
            Property(
                property_id=UUID("11111111-1111-1111-1111-111111111111"),
                tenant_id=tenant_id,
                name="HQ",
                address="Main Street 1",
                created_at=datetime(2026, 3, 12, tzinfo=UTC),
            ),
            Property(
                property_id=UUID("22222222-2222-2222-2222-222222222222"),
                tenant_id=tenant_id,
                name="Annex",
                address="Side Street 5",
                created_at=datetime(2026, 3, 11, tzinfo=UTC),
            ),
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


def _get_properties_event(
    *, tenant_id: str = "tenant-from-token", user_id: str = "user-123"
) -> dict:
    event = _event_with_auth(tenant_id=tenant_id, user_id=user_id)
    event["queryStringParameters"] = {"tenant_id": "tenant-from-client-should-be-ignored"}
    return event


def test_list_properties_uses_auth_tenant_not_client_input() -> None:
    db = _FakeDb()
    event = _get_properties_event(tenant_id="tenant-auth", user_id="user-auth")

    payload = list_properties(event, db)

    assert db.list_calls == ["tenant-auth"]
    assert payload == {
        "items": [
            {
                "property_id": "11111111-1111-1111-1111-111111111111",
                "tenant_id": "tenant-auth",
                "name": "HQ",
                "address": "Main Street 1",
                "created_at": "2026-03-12T00:00:00+00:00",
            },
            {
                "property_id": "22222222-2222-2222-2222-222222222222",
                "tenant_id": "tenant-auth",
                "name": "Annex",
                "address": "Side Street 5",
                "created_at": "2026-03-11T00:00:00+00:00",
            },
        ]
    }


def test_list_properties_requires_jwt_claims() -> None:
    db = _FakeDb()

    with pytest.raises(AuthError, match="Missing JWT claims."):
        list_properties({}, db)


def test_create_property_uses_auth_tenant_not_body_tenant() -> None:
    db = _FakeDb()
    event = _event_with_auth(tenant_id="tenant-auth", user_id="user-auth")
    body = {
        "tenant_id": "tenant-body-should-be-ignored",
        "name": "HQ",
        "address": "Main Street 1",
    }

    payload = create_property(event, db, body)

    assert db.calls == [
        {
            "tenant_id": "tenant-auth",
            "actor_user_id": "user-auth",
            "name": "HQ",
            "address": "Main Street 1",
        }
    ]
    assert payload["tenant_id"] == "tenant-auth"
    assert payload["name"] == "HQ"
    assert payload["address"] == "Main Street 1"
    assert "property_id" in payload
    assert payload["created_at"] == "2026-03-12T00:00:00+00:00"


def test_create_property_requires_name_and_address() -> None:
    db = _FakeDb()
    event = _event_with_auth()

    with pytest.raises(ValueError, match="Fields 'name' and 'address' are required."):
        create_property(event, db, {"name": "only-name"})
