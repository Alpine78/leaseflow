from __future__ import annotations

from typing import Any

from app.db import Database

_INTERNAL_ACTOR = "leaseflow.internal"
_DUPLICATE_MESSAGE = "Notification contact already exists for tenant."


def configure_notification_contact(event: dict[str, Any], db: Database) -> dict[str, bool]:
    detail = event.get("detail") or {}
    tenant_id = _required_detail(detail, "tenant_id", "Notification contact tenant_id is required.")
    email = _required_detail(detail, "email", "Notification contact email is required.")

    try:
        db.create_notification_contact(
            tenant_id=tenant_id,
            actor_user_id=_INTERNAL_ACTOR,
            email=email,
            enabled=True,
            audit_source=_INTERNAL_ACTOR,
        )
    except ValueError as exc:
        if str(exc) != _DUPLICATE_MESSAGE:
            raise
        return _configure_existing_contact(db, tenant_id=tenant_id, email=email)

    return _payload(created=True, updated=False, enabled=True)


def _configure_existing_contact(
    db: Database,
    *,
    tenant_id: str,
    email: str,
) -> dict[str, bool]:
    normalized_email = email.strip().lower()
    contacts = db.list_notification_contacts(tenant_id=tenant_id)

    for contact in contacts:
        if contact.email.strip().lower() != normalized_email:
            continue
        if contact.enabled:
            return _payload(created=False, updated=False, enabled=True)
        db.set_notification_contact_enabled(
            tenant_id=tenant_id,
            actor_user_id=_INTERNAL_ACTOR,
            contact_id=contact.contact_id,
            enabled=True,
            audit_source=_INTERNAL_ACTOR,
        )
        return _payload(created=False, updated=True, enabled=True)

    raise ValueError(_DUPLICATE_MESSAGE)


def _required_detail(detail: dict[str, Any], key: str, error_message: str) -> str:
    value = str(detail.get(key, "")).strip()
    if not value:
        raise ValueError(error_message)
    return value


def _payload(*, created: bool, updated: bool, enabled: bool) -> dict[str, bool]:
    return {
        "configured": True,
        "created": created,
        "updated": updated,
        "enabled": enabled,
    }
