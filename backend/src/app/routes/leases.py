from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.auth import extract_auth_context
from app.db import Database, leases_to_dict


def list_leases(event: dict[str, Any], db: Database) -> dict[str, Any]:
    auth = extract_auth_context(event)
    items = db.list_leases(tenant_id=auth.tenant_id)
    return {"items": leases_to_dict(items)}


def create_lease(event: dict[str, Any], db: Database, body: dict[str, Any]) -> dict[str, Any]:
    auth = extract_auth_context(event)

    property_id_raw = str(body.get("property_id", "")).strip()
    resident_name = str(body.get("resident_name", "")).strip()
    rent_due_day_of_month_raw = body.get("rent_due_day_of_month")
    start_date_raw = str(body.get("start_date", "")).strip()
    end_date_raw = str(body.get("end_date", "")).strip()

    if (
        not property_id_raw
        or not resident_name
        or rent_due_day_of_month_raw in (None, "")
        or not start_date_raw
        or not end_date_raw
    ):
        raise ValueError(
            "Fields 'property_id', 'resident_name', "
            "'rent_due_day_of_month', 'start_date', and 'end_date' are required."
        )

    try:
        property_id = UUID(property_id_raw)
    except ValueError as exc:
        raise ValueError("Field 'property_id' must be a valid UUID.") from exc

    rent_due_day_of_month = _parse_rent_due_day_of_month(rent_due_day_of_month_raw)
    start_date, end_date = _parse_dates(start_date_raw, end_date_raw)
    if end_date < start_date:
        raise ValueError("'end_date' must be on or after 'start_date'.")

    created = db.create_lease(
        tenant_id=auth.tenant_id,
        actor_user_id=auth.user_id,
        property_id=property_id,
        resident_name=resident_name,
        rent_due_day_of_month=rent_due_day_of_month,
        start_date=start_date,
        end_date=end_date,
    )
    return leases_to_dict([created])[0]


def _parse_dates(start_date_raw: str, end_date_raw: str) -> tuple[date, date]:
    try:
        return date.fromisoformat(start_date_raw), date.fromisoformat(end_date_raw)
    except ValueError as exc:
        raise ValueError("Fields 'start_date' and 'end_date' must use YYYY-MM-DD.") from exc


def _parse_rent_due_day_of_month(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("Field 'rent_due_day_of_month' must be an integer between 1 and 31.")

    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Field 'rent_due_day_of_month' must be an integer between 1 and 31."
        ) from exc

    if parsed < 1 or parsed > 31:
        raise ValueError("Field 'rent_due_day_of_month' must be an integer between 1 and 31.")

    return parsed
