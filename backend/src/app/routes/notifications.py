from __future__ import annotations

from typing import Any

from app.auth import extract_auth_context
from app.db import Database, notifications_to_dict


def list_notifications(event: dict[str, Any], db: Database) -> dict[str, Any]:
    auth = extract_auth_context(event)
    items = db.list_notifications(tenant_id=auth.tenant_id)
    return {"items": notifications_to_dict(items)}
