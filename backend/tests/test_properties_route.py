from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models import Property
from app.routes.properties import create_property


class _FakeDb:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

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
