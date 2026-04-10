from __future__ import annotations

import json
from datetime import date
from typing import Any
from uuid import UUID

from app.auth import extract_auth_context
from app.db import Database, leases_to_dict

_MUTABLE_FIELDS = ("resident_name", "rent_due_day_of_month", "start_date", "end_date")


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


def update_lease(event: dict[str, Any], db: Database, lease_id: UUID) -> dict[str, Any]:
    auth = extract_auth_context(event)
    updated = db.update_lease(
        tenant_id=auth.tenant_id,
        actor_user_id=auth.user_id,
        lease_id=lease_id,
        updates=_lease_update_body(event),
    )
    return leases_to_dict([updated])[0]


def _lease_update_body(event: dict[str, Any]) -> dict[str, object]:
    body = _json_body(event)
    if not body:
        raise ValueError(
            "At least one of 'resident_name', 'rent_due_day_of_month', 'start_date', or 'end_date' is required."
        )

    unsupported_fields = set(body) - set(_MUTABLE_FIELDS)
    if unsupported_fields:
        raise ValueError(
            "Only fields 'resident_name', 'rent_due_day_of_month', 'start_date', and 'end_date' can be updated."
        )

    updates: dict[str, object] = {}
    if "resident_name" in body:
        resident_name = str(body["resident_name"]).strip()
        if not resident_name:
            raise ValueError("Field 'resident_name' must not be empty.")
        updates["resident_name"] = resident_name
    if "rent_due_day_of_month" in body:
        updates["rent_due_day_of_month"] = _parse_rent_due_day_of_month(
            body["rent_due_day_of_month"]
        )
    if "start_date" in body:
        updates["start_date"] = _parse_date(str(body["start_date"]).strip())
    if "end_date" in body:
        updates["end_date"] = _parse_date(str(body["end_date"]).strip())

    if (
        "start_date" in updates
        and "end_date" in updates
        and updates["end_date"] < updates["start_date"]
    ):
        raise ValueError("'end_date' must be on or after 'start_date'.")

    if not updates:
        raise ValueError(
            "At least one of 'resident_name', 'rent_due_day_of_month', 'start_date', or 'end_date' is required."
        )

    return updates


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


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Fields 'start_date' and 'end_date' must use YYYY-MM-DD.") from exc


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
