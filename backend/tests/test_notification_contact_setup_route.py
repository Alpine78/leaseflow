from __future__ import annotations

import importlib
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import pytest


def _route_module():
    return importlib.import_module("app.routes.notification_contact_setup")


@dataclass(slots=True)
class _Contact:
    contact_id: UUID
    tenant_id: str
    email: str
    enabled: bool
    created_at: datetime


class _FakeDb:
    def __init__(self, contacts: list[_Contact] | None = None) -> None:
        self.contacts = contacts or []
        self.create_calls: list[tuple[str, str, str, bool, str]] = []
        self.list_calls: list[tuple[str, bool]] = []
        self.enable_calls: list[tuple[str, str, UUID, bool, str]] = []

    def create_notification_contact(
        self,
        tenant_id: str,
        actor_user_id: str,
        email: str,
        enabled: bool = True,
        audit_source: str = "api",
    ) -> _Contact:
        self.create_calls.append((tenant_id, actor_user_id, email, enabled, audit_source))
        normalized_email = email.strip().lower()
        if any(contact.email == normalized_email for contact in self.contacts):
            raise ValueError("Notification contact already exists for tenant.")

        contact = _contact(
            tenant_id=tenant_id,
            email=normalized_email,
            enabled=enabled,
        )
        self.contacts.append(contact)
        return contact

    def list_notification_contacts(
        self,
        tenant_id: str,
        enabled_only: bool = False,
    ) -> list[_Contact]:
        self.list_calls.append((tenant_id, enabled_only))
        contacts = [contact for contact in self.contacts if contact.tenant_id == tenant_id]
        if enabled_only:
            return [contact for contact in contacts if contact.enabled]
        return contacts

    def set_notification_contact_enabled(
        self,
        tenant_id: str,
        actor_user_id: str,
        contact_id: UUID,
        enabled: bool,
        audit_source: str = "api",
    ) -> _Contact:
        self.enable_calls.append(
            (tenant_id, actor_user_id, contact_id, enabled, audit_source)
        )
        for index, contact in enumerate(self.contacts):
            if contact.tenant_id == tenant_id and contact.contact_id == contact_id:
                updated = _Contact(
                    contact_id=contact.contact_id,
                    tenant_id=contact.tenant_id,
                    email=contact.email,
                    enabled=enabled,
                    created_at=contact.created_at,
                )
                self.contacts[index] = updated
                return updated
        raise LookupError("Notification contact not found for tenant.")


def _event(
    *,
    tenant_id: str | None = "tenant-auth",
    email: str | None = " Contact.One+SES@Example.COM ",
) -> dict:
    detail = {}
    if tenant_id is not None:
        detail["tenant_id"] = tenant_id
    if email is not None:
        detail["email"] = email
    return {
        "source": "leaseflow.internal",
        "detail-type": "configure_notification_contact",
        "detail": detail,
    }


def _contact(
    *,
    tenant_id: str = "tenant-auth",
    email: str = "contact.one+ses@example.com",
    enabled: bool = True,
) -> _Contact:
    return _Contact(
        contact_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        tenant_id=tenant_id,
        email=email,
        enabled=enabled,
        created_at=datetime(2026, 5, 4, tzinfo=timezone.utc),
    )


def test_configure_notification_contact_creates_enabled_contact_with_safe_payload() -> None:
    route = _route_module()
    db = _FakeDb()

    payload = route.configure_notification_contact(_event(), db)

    assert db.create_calls == [
        (
            "tenant-auth",
            "leaseflow.internal",
            "Contact.One+SES@Example.COM",
            True,
            "leaseflow.internal",
        )
    ]
    assert payload == {
        "configured": True,
        "created": True,
        "updated": False,
        "enabled": True,
    }
    assert "tenant-auth" not in str(payload)
    assert "contact.one+ses@example.com" not in str(payload)
    assert "cccccccc" not in str(payload)


def test_configure_notification_contact_reenables_disabled_existing_contact() -> None:
    route = _route_module()
    existing = _contact(enabled=False)
    db = _FakeDb([existing])

    payload = route.configure_notification_contact(_event(), db)

    assert db.create_calls == [
        (
            "tenant-auth",
            "leaseflow.internal",
            "Contact.One+SES@Example.COM",
            True,
            "leaseflow.internal",
        )
    ]
    assert db.list_calls == [("tenant-auth", False)]
    assert db.enable_calls == [
        (
            "tenant-auth",
            "leaseflow.internal",
            existing.contact_id,
            True,
            "leaseflow.internal",
        )
    ]
    assert payload == {
        "configured": True,
        "created": False,
        "updated": True,
        "enabled": True,
    }


def test_configure_notification_contact_leaves_enabled_existing_contact_unchanged() -> None:
    route = _route_module()
    db = _FakeDb([_contact(enabled=True)])

    payload = route.configure_notification_contact(_event(), db)

    assert db.list_calls == [("tenant-auth", False)]
    assert db.enable_calls == []
    assert payload == {
        "configured": True,
        "created": False,
        "updated": False,
        "enabled": True,
    }


@pytest.mark.parametrize(
    ("event", "message"),
    [
        (_event(tenant_id=None), "Notification contact tenant_id is required."),
        (_event(tenant_id="   "), "Notification contact tenant_id is required."),
        (_event(email=None), "Notification contact email is required."),
        (_event(email="   "), "Notification contact email is required."),
    ],
)
def test_configure_notification_contact_rejects_missing_or_blank_input(
    event: dict,
    message: str,
) -> None:
    route = _route_module()

    with pytest.raises(ValueError, match=message):
        route.configure_notification_contact(event, _FakeDb())
