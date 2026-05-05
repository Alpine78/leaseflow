from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.auth import extract_auth_context
from app.db import Database
from app.models import NotificationContact

_DUPLICATE_MESSAGE = "Notification contact already exists for tenant."


def list_notification_contacts(event: dict[str, Any], db: Database) -> dict[str, Any]:
    auth = extract_auth_context(event)
    items = db.list_notification_contacts(tenant_id=auth.tenant_id)
    return {"items": notification_contacts_to_dict(items)}


def create_notification_contact(
    event: dict[str, Any],
    db: Database,
    body: dict[str, Any],
) -> dict[str, Any]:
    auth = extract_auth_context(event)
    email = _create_body_email(body)

    try:
        created = db.create_notification_contact(
            tenant_id=auth.tenant_id,
            actor_user_id=auth.user_id,
            email=email,
            enabled=True,
        )
    except ValueError as exc:
        if str(exc) != _DUPLICATE_MESSAGE:
            raise
        return notification_contact_to_dict(
            _reenable_disabled_duplicate(
                db,
                tenant_id=auth.tenant_id,
                actor_user_id=auth.user_id,
                email=email,
            )
        )

    return notification_contact_to_dict(created)


def update_notification_contact(
    event: dict[str, Any],
    db: Database,
    contact_id: UUID,
) -> dict[str, Any]:
    auth = extract_auth_context(event)
    enabled = _update_body_enabled(event)
    updated = db.set_notification_contact_enabled(
        tenant_id=auth.tenant_id,
        actor_user_id=auth.user_id,
        contact_id=contact_id,
        enabled=enabled,
    )
    return notification_contact_to_dict(updated)


def notification_contact_to_dict(item: NotificationContact) -> dict[str, Any]:
    return {
        "contact_id": str(item.contact_id),
        "email": item.email,
        "enabled": item.enabled,
        "created_at": item.created_at.isoformat(),
    }


def notification_contacts_to_dict(
    items: list[NotificationContact],
) -> list[dict[str, Any]]:
    return [notification_contact_to_dict(item) for item in items]


def _create_body_email(body: dict[str, Any]) -> str:
    unsupported_fields = set(body) - {"email"}
    if unsupported_fields:
        raise ValueError("Only field 'email' can be provided.")

    email = str(body.get("email", "")).strip()
    if not email:
        raise ValueError("Field 'email' is required.")
    return email


def _update_body_enabled(event: dict[str, Any]) -> bool:
    body = _json_body(event)
    if set(body) != {"enabled"}:
        raise ValueError("Only field 'enabled' can be updated.")

    enabled = body["enabled"]
    if not isinstance(enabled, bool):
        raise ValueError("Field 'enabled' must be a boolean.")
    return enabled


def _json_body(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("body")
    if raw in (None, ""):
        return {}

    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON request body.") from exc

    if not isinstance(body, dict):
        raise ValueError("JSON body must be an object.")
    return body


def _reenable_disabled_duplicate(
    db: Database,
    *,
    tenant_id: str,
    actor_user_id: str,
    email: str,
) -> NotificationContact:
    normalized_email = email.strip().lower()
    contacts = db.list_notification_contacts(tenant_id=tenant_id)

    for contact in contacts:
        if contact.email.strip().lower() != normalized_email:
            continue
        if contact.enabled:
            raise ValueError(_DUPLICATE_MESSAGE)
        return db.set_notification_contact_enabled(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            contact_id=contact.contact_id,
            enabled=True,
        )

    raise ValueError(_DUPLICATE_MESSAGE)
