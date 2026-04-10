from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.auth import extract_auth_context
from app.db import Database, properties_to_dict

_MUTABLE_FIELDS = ("name", "address")


def list_properties(event: dict[str, Any], db: Database) -> dict[str, Any]:
    auth = extract_auth_context(event)
    items = db.list_properties(tenant_id=auth.tenant_id)
    return {"items": properties_to_dict(items)}


def create_property(event: dict[str, Any], db: Database, body: dict[str, Any]) -> dict[str, Any]:
    auth = extract_auth_context(event)

    name = str(body.get("name", "")).strip()
    address = str(body.get("address", "")).strip()
    if not name or not address:
        raise ValueError("Fields 'name' and 'address' are required.")

    # tenant_id from request body is intentionally ignored.
    created = db.create_property(
        tenant_id=auth.tenant_id,
        actor_user_id=auth.user_id,
        name=name,
        address=address,
    )
    return {
        "property_id": str(created.property_id),
        "tenant_id": created.tenant_id,
        "name": created.name,
        "address": created.address,
        "created_at": created.created_at.isoformat(),
    }


def update_property(event: dict[str, Any], db: Database, property_id: UUID) -> dict[str, Any]:
    auth = extract_auth_context(event)
    updated = db.update_property(
        tenant_id=auth.tenant_id,
        actor_user_id=auth.user_id,
        property_id=property_id,
        updates=_property_update_body(event),
    )
    return properties_to_dict([updated])[0]


def _property_update_body(event: dict[str, Any]) -> dict[str, str]:
    body = _json_body(event)
    if not body:
        raise ValueError("At least one of 'name' or 'address' is required.")

    unsupported_fields = set(body) - set(_MUTABLE_FIELDS)
    if unsupported_fields:
        raise ValueError("Only fields 'name' and 'address' can be updated.")

    updates: dict[str, str] = {}
    for field in _MUTABLE_FIELDS:
        if field not in body:
            continue

        value = str(body[field]).strip()
        if not value:
            raise ValueError(f"Field '{field}' must not be empty.")
        updates[field] = value

    if not updates:
        raise ValueError("At least one of 'name' or 'address' is required.")

    return updates


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
