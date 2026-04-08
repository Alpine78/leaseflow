from __future__ import annotations

from datetime import date
from typing import Any

from app.db import Database


def scan_due_lease_reminders(event: dict[str, Any], db: Database) -> dict[str, Any]:
    detail = event.get("detail") or {}
    tenant_id = _parse_tenant_id(detail)

    days = _parse_days(detail)
    as_of_date = _parse_as_of_date(detail)
    result = db.create_due_lease_reminder_notifications(
        tenant_id=tenant_id,
        as_of_date=as_of_date,
        days=days,
    )
    return {
        "tenant_id": result.tenant_id,
        "as_of_date": result.as_of_date.isoformat(),
        "days": result.days,
        "tenant_count": result.tenant_count,
        "candidate_count": result.candidate_count,
        "created_count": result.created_count,
        "duplicate_count": result.duplicate_count,
    }


def _parse_tenant_id(detail: dict[str, Any]) -> str | None:
    tenant_id = str(detail.get("tenant_id", "")).strip()
    return tenant_id or None


def _parse_days(detail: dict[str, Any]) -> int:
    raw_days = detail.get("days")
    if raw_days in (None, ""):
        return 7
    if isinstance(raw_days, bool):
        raise ValueError("Detail field 'days' must be an integer between 1 and 31.")

    try:
        days = int(raw_days)
    except (TypeError, ValueError) as exc:
        raise ValueError("Detail field 'days' must be an integer between 1 and 31.") from exc

    if days < 1 or days > 31:
        raise ValueError("Detail field 'days' must be an integer between 1 and 31.")

    return days


def _parse_as_of_date(detail: dict[str, Any]) -> date:
    raw_as_of_date = detail.get("as_of_date")
    if raw_as_of_date in (None, ""):
        return _today()

    try:
        return date.fromisoformat(str(raw_as_of_date))
    except ValueError as exc:
        raise ValueError("Detail field 'as_of_date' must use YYYY-MM-DD.") from exc


def _today() -> date:
    return date.today()
