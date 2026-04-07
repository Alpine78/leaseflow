from __future__ import annotations

from datetime import date
from typing import Any

from app.auth import extract_auth_context
from app.db import Database, lease_reminders_to_dict


def list_due_lease_reminders(event: dict[str, Any], db: Database) -> dict[str, Any]:
    auth = extract_auth_context(event)
    days = _parse_days(event.get("queryStringParameters") or {})
    items = db.list_due_lease_reminders(
        tenant_id=auth.tenant_id,
        as_of_date=_today(),
        days=days,
    )
    return {"items": lease_reminders_to_dict(items)}


def _parse_days(query_params: dict[str, Any]) -> int:
    raw_days = query_params.get("days")
    if raw_days in (None, ""):
        return 7

    try:
        days = int(raw_days)
    except (TypeError, ValueError) as exc:
        raise ValueError("Query parameter 'days' must be an integer between 1 and 31.") from exc

    if days < 1 or days > 31:
        raise ValueError("Query parameter 'days' must be an integer between 1 and 31.")

    return days


def _today() -> date:
    return date.today()
