from __future__ import annotations

import importlib
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.auth import AuthError


def _contacts_module():
    return importlib.import_module("app.routes.notification_contacts")


@dataclass(slots=True)
class _ContactRecord:
    contact_id: UUID
    tenant_id: str
    email: str
    enabled: bool
    created_at: datetime


class _FakeDb:
    def __init__(self) -> None:
        self.contacts: list[_ContactRecord] = [
            _contact(
                contact_id=UUID("11111111-1111-1111-1111-111111111111"),
                tenant_id="tenant-auth",
                email="enabled@example.test",
                enabled=True,
            ),
            _contact(
                contact_id=UUID("22222222-2222-2222-2222-222222222222"),
                tenant_id="tenant-auth",
                email="disabled@example.test",
                enabled=False,
            ),
        ]
        self.create_calls: list[dict[str, object]] = []
        self.list_calls: list[str] = []
        self.update_calls: list[dict[str, object]] = []

    def list_notification_contacts(self, tenant_id: str) -> list[_ContactRecord]:
        self.list_calls.append(tenant_id)
        return [contact for contact in self.contacts if contact.tenant_id == tenant_id]

    def create_notification_contact(
        self,
        tenant_id: str,
        actor_user_id: str,
        email: str,
        enabled: bool = True,
    ) -> _ContactRecord:
        self.create_calls.append(
            {
                "tenant_id": tenant_id,
                "actor_user_id": actor_user_id,
                "email": email,
                "enabled": enabled,
            }
        )
        normalized_email = email.strip().lower()
        if any(
            contact.tenant_id == tenant_id and contact.email.strip().lower() == normalized_email
            for contact in self.contacts
        ):
            raise ValueError("Notification contact already exists for tenant.")
        created = _contact(
            contact_id=UUID("33333333-3333-3333-3333-333333333333"),
            tenant_id=tenant_id,
            email=normalized_email,
            enabled=enabled,
        )
        self.contacts.append(created)
        return created

    def set_notification_contact_enabled(
        self,
        tenant_id: str,
        actor_user_id: str,
        contact_id: UUID,
        enabled: bool,
    ) -> _ContactRecord:
        self.update_calls.append(
            {
                "tenant_id": tenant_id,
                "actor_user_id": actor_user_id,
                "contact_id": contact_id,
                "enabled": enabled,
            }
        )
        for index, contact in enumerate(self.contacts):
            if contact.tenant_id == tenant_id and contact.contact_id == contact_id:
                updated = _contact(
                    contact_id=contact.contact_id,
                    tenant_id=contact.tenant_id,
                    email=contact.email,
                    enabled=enabled,
                )
                self.contacts[index] = updated
                return updated
        raise LookupError("Notification contact not found for tenant.")


def _contact(
    *,
    contact_id: UUID,
    tenant_id: str,
    email: str,
    enabled: bool,
) -> _ContactRecord:
    return _ContactRecord(
        contact_id=contact_id,
        tenant_id=tenant_id,
        email=email,
        enabled=enabled,
        created_at=datetime(2026, 5, 5, tzinfo=UTC),
    )


def _event_with_auth(*, tenant_id: str = "tenant-auth", user_id: str = "user-auth") -> dict:
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


def test_list_notification_contacts_uses_auth_tenant_and_excludes_tenant_id() -> None:
    contacts = _contacts_module()
    db = _FakeDb()
    event = _event_with_auth()
    event["queryStringParameters"] = {"tenant_id": "tenant-from-client"}

    payload = contacts.list_notification_contacts(event, db)

    assert db.list_calls == ["tenant-auth"]
    assert payload == {
        "items": [
            {
                "contact_id": "11111111-1111-1111-1111-111111111111",
                "email": "enabled@example.test",
                "enabled": True,
                "created_at": "2026-05-05T00:00:00+00:00",
            },
            {
                "contact_id": "22222222-2222-2222-2222-222222222222",
                "email": "disabled@example.test",
                "enabled": False,
                "created_at": "2026-05-05T00:00:00+00:00",
            },
        ]
    }


def test_create_notification_contact_uses_auth_context_and_excludes_tenant_id() -> None:
    contacts = _contacts_module()
    db = _FakeDb()
    event = _event_with_auth()

    payload = contacts.create_notification_contact(event, db, {"email": " New@Example.TEST "})

    assert db.create_calls == [
        {
            "tenant_id": "tenant-auth",
            "actor_user_id": "user-auth",
            "email": "New@Example.TEST",
            "enabled": True,
        }
    ]
    assert payload == {
        "contact_id": "33333333-3333-3333-3333-333333333333",
        "email": "new@example.test",
        "enabled": True,
        "created_at": "2026-05-05T00:00:00+00:00",
    }


def test_create_notification_contact_reenables_disabled_duplicate() -> None:
    contacts = _contacts_module()
    db = _FakeDb()
    event = _event_with_auth()

    payload = contacts.create_notification_contact(event, db, {"email": "DISABLED@example.test"})

    assert db.update_calls == [
        {
            "tenant_id": "tenant-auth",
            "actor_user_id": "user-auth",
            "contact_id": UUID("22222222-2222-2222-2222-222222222222"),
            "enabled": True,
        }
    ]
    assert payload["contact_id"] == "22222222-2222-2222-2222-222222222222"
    assert payload["enabled"] is True
    assert "tenant_id" not in payload


def test_create_notification_contact_rejects_enabled_duplicate() -> None:
    contacts = _contacts_module()
    db = _FakeDb()
    event = _event_with_auth()

    with pytest.raises(ValueError, match="Notification contact already exists for tenant."):
        contacts.create_notification_contact(event, db, {"email": "ENABLED@example.test"})


def test_create_notification_contact_rejects_unsupported_body_fields() -> None:
    contacts = _contacts_module()
    db = _FakeDb()
    event = _event_with_auth()

    with pytest.raises(ValueError, match="Only field 'email' can be provided."):
        contacts.create_notification_contact(
            event,
            db,
            {"email": "contact@example.test", "tenant_id": "tenant-from-body"},
        )


def test_update_notification_contact_enabled_uses_auth_context_and_excludes_tenant_id() -> None:
    contacts = _contacts_module()
    db = _FakeDb()
    event = _event_with_auth()
    event["queryStringParameters"] = {"tenant_id": "tenant-from-query"}
    event["body"] = '{"enabled": false}'

    payload = contacts.update_notification_contact(
        event,
        db,
        UUID("11111111-1111-1111-1111-111111111111"),
    )

    assert db.update_calls == [
        {
            "tenant_id": "tenant-auth",
            "actor_user_id": "user-auth",
            "contact_id": UUID("11111111-1111-1111-1111-111111111111"),
            "enabled": False,
        }
    ]
    assert payload == {
        "contact_id": "11111111-1111-1111-1111-111111111111",
        "email": "enabled@example.test",
        "enabled": False,
        "created_at": "2026-05-05T00:00:00+00:00",
    }


def test_update_notification_contact_rejects_non_boolean_enabled() -> None:
    contacts = _contacts_module()
    db = _FakeDb()
    event = _event_with_auth()
    event["body"] = '{"enabled": "false"}'

    with pytest.raises(ValueError, match="Field 'enabled' must be a boolean."):
        contacts.update_notification_contact(
            event,
            db,
            UUID("11111111-1111-1111-1111-111111111111"),
        )


def test_update_notification_contact_rejects_unsupported_body_fields() -> None:
    contacts = _contacts_module()
    db = _FakeDb()
    event = _event_with_auth()
    event["body"] = '{"enabled": false, "tenant_id": "tenant-from-body"}'

    with pytest.raises(ValueError, match="Only field 'enabled' can be updated."):
        contacts.update_notification_contact(
            event,
            db,
            UUID("11111111-1111-1111-1111-111111111111"),
        )


def test_notification_contact_routes_require_jwt_claims() -> None:
    contacts = _contacts_module()
    db = _FakeDb()

    with pytest.raises(AuthError, match="Missing JWT claims."):
        contacts.list_notification_contacts({}, db)

    with pytest.raises(AuthError, match="Missing JWT claims."):
        contacts.create_notification_contact({}, db, {"email": "contact@example.test"})
