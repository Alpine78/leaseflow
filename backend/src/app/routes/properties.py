from __future__ import annotations

from typing import Any

from app.auth import extract_auth_context
from app.db import Database, properties_to_dict


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
