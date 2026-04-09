from __future__ import annotations

from typing import Any
from uuid import UUID

from app.auth import extract_auth_context
from app.db import Database, notification_to_dict, notifications_to_dict


def list_notifications(event: dict[str, Any], db: Database) -> dict[str, Any]:
    auth = extract_auth_context(event)
    items = db.list_notifications(tenant_id=auth.tenant_id)
    return {"items": notifications_to_dict(items)}


def mark_notification_read(
    event: dict[str, Any],
    db: Database,
    notification_id: UUID,
) -> dict[str, Any]:
    auth = extract_auth_context(event)
    item = db.mark_notification_read(
        tenant_id=auth.tenant_id,
        notification_id=notification_id,
    )
    return notification_to_dict(item)
