from __future__ import annotations

import calendar
from collections.abc import Sequence
from datetime import date, timedelta
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app.config import Settings
from app.models import Lease, LeaseReminderCandidate, Property


class Database:
    def __init__(self, settings: Settings) -> None:
        self._dsn = settings.db_dsn()

    def list_due_lease_reminders(
        self,
        tenant_id: str,
        as_of_date: date,
        days: int,
    ) -> list[LeaseReminderCandidate]:
        range_end = as_of_date + timedelta(days=days)
        sql = """
            SELECT
                lease_id,
                tenant_id,
                property_id,
                resident_name,
                rent_due_day_of_month,
                start_date,
                end_date
            FROM leases
            WHERE tenant_id = %s
              AND rent_due_day_of_month IS NOT NULL
              AND start_date <= %s
              AND end_date >= %s
            ORDER BY created_at DESC
        """
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            rows = conn.execute(sql, (tenant_id, range_end, as_of_date)).fetchall()

        candidates: list[LeaseReminderCandidate] = []
        for row in rows:
            due_date = _next_due_date(
                as_of_date=as_of_date,
                due_day_of_month=int(row["rent_due_day_of_month"]),
            )
            if due_date > range_end:
                continue
            if due_date < row["start_date"] or due_date > row["end_date"]:
                continue

            candidates.append(
                LeaseReminderCandidate(
                    lease_id=row["lease_id"],
                    tenant_id=row["tenant_id"],
                    property_id=row["property_id"],
                    resident_name=row["resident_name"],
                    rent_due_day_of_month=int(row["rent_due_day_of_month"]),
                    due_date=due_date,
                    days_until_due=(due_date - as_of_date).days,
                )
            )

        candidates.sort(key=lambda item: (item.due_date, item.lease_id))
        return candidates

    def list_leases(self, tenant_id: str) -> list[Lease]:
        sql = """
            SELECT
                lease_id,
                tenant_id,
                property_id,
                resident_name,
                rent_due_day_of_month,
                start_date,
                end_date,
                created_at
            FROM leases
            WHERE tenant_id = %s
            ORDER BY created_at DESC
        """
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            rows = conn.execute(sql, (tenant_id,)).fetchall()
        return [self._row_to_lease(row) for row in rows]

    def list_properties(self, tenant_id: str) -> list[Property]:
        sql = """
            SELECT property_id, tenant_id, name, address, created_at
            FROM properties
            WHERE tenant_id = %s
            ORDER BY created_at DESC
        """
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            rows = conn.execute(sql, (tenant_id,)).fetchall()
        return [self._row_to_property(row) for row in rows]

    def create_lease(
        self,
        tenant_id: str,
        actor_user_id: str,
        property_id: UUID,
        resident_name: str,
        rent_due_day_of_month: int,
        start_date: date,
        end_date: date,
    ) -> Lease:
        lease_sql = """
            INSERT INTO leases (
                tenant_id, property_id, resident_name, rent_due_day_of_month, start_date, end_date
            )
            SELECT p.tenant_id, p.property_id, %s, %s, %s, %s
            FROM properties p
            WHERE p.tenant_id = %s AND p.property_id = %s
            RETURNING
                lease_id,
                tenant_id,
                property_id,
                resident_name,
                rent_due_day_of_month,
                start_date,
                end_date,
                created_at
        """
        audit_sql = """
            INSERT INTO audit_logs (
                tenant_id, actor_user_id, action, entity_type, entity_id, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
        """
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            with conn.transaction():
                lease_row = conn.execute(
                    lease_sql,
                    (
                        resident_name,
                        rent_due_day_of_month,
                        start_date,
                        end_date,
                        tenant_id,
                        property_id,
                    ),
                ).fetchone()
                if not lease_row:
                    raise ValueError("Property not found for tenant.")
                conn.execute(
                    audit_sql,
                    (
                        tenant_id,
                        actor_user_id,
                        "lease.create",
                        "lease",
                        lease_row["lease_id"],
                        '{"source":"api"}',
                    ),
                )
        return self._row_to_lease(lease_row)

    def create_property(
        self,
        tenant_id: str,
        actor_user_id: str,
        name: str,
        address: str,
    ) -> Property:
        property_sql = """
            INSERT INTO properties (tenant_id, name, address)
            VALUES (%s, %s, %s)
            RETURNING property_id, tenant_id, name, address, created_at
        """
        audit_sql = """
            INSERT INTO audit_logs (
                tenant_id, actor_user_id, action, entity_type, entity_id, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
        """
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            with conn.transaction():
                property_row = conn.execute(property_sql, (tenant_id, name, address)).fetchone()
                if not property_row:
                    raise RuntimeError("Failed to create property.")
                conn.execute(
                    audit_sql,
                    (
                        tenant_id,
                        actor_user_id,
                        "property.create",
                        "property",
                        property_row["property_id"],
                        '{"source":"api"}',
                    ),
                )
        return self._row_to_property(property_row)

    @staticmethod
    def _row_to_property(row: dict[str, Any]) -> Property:
        return Property(
            property_id=row["property_id"],
            tenant_id=row["tenant_id"],
            name=row["name"],
            address=row["address"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_lease(row: dict[str, Any]) -> Lease:
        return Lease(
            lease_id=row["lease_id"],
            tenant_id=row["tenant_id"],
            property_id=row["property_id"],
            resident_name=row["resident_name"],
            rent_due_day_of_month=row["rent_due_day_of_month"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            created_at=row["created_at"],
        )


def properties_to_dict(items: Sequence[Property]) -> list[dict[str, Any]]:
    return [
        {
            "property_id": str(item.property_id),
            "tenant_id": item.tenant_id,
            "name": item.name,
            "address": item.address,
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]


def leases_to_dict(items: Sequence[Lease]) -> list[dict[str, Any]]:
    return [
        {
            "lease_id": str(item.lease_id),
            "tenant_id": item.tenant_id,
            "property_id": str(item.property_id),
            "resident_name": item.resident_name,
            "rent_due_day_of_month": item.rent_due_day_of_month,
            "start_date": item.start_date.isoformat(),
            "end_date": item.end_date.isoformat(),
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]


def lease_reminders_to_dict(items: Sequence[LeaseReminderCandidate]) -> list[dict[str, Any]]:
    return [
        {
            "lease_id": str(item.lease_id),
            "tenant_id": item.tenant_id,
            "property_id": str(item.property_id),
            "resident_name": item.resident_name,
            "rent_due_day_of_month": item.rent_due_day_of_month,
            "due_date": item.due_date.isoformat(),
            "days_until_due": item.days_until_due,
        }
        for item in items
    ]


def _next_due_date(as_of_date: date, due_day_of_month: int) -> date:
    current_month_due = _month_due_date(
        year=as_of_date.year,
        month=as_of_date.month,
        due_day_of_month=due_day_of_month,
    )
    if current_month_due >= as_of_date:
        return current_month_due

    next_month_anchor = as_of_date.replace(day=28) + timedelta(days=4)
    return _month_due_date(
        year=next_month_anchor.year,
        month=next_month_anchor.month,
        due_day_of_month=due_day_of_month,
    )


def _month_due_date(year: int, month: int, due_day_of_month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(due_day_of_month, last_day))
