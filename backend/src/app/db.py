from __future__ import annotations

import calendar
import json
from collections.abc import Sequence
from datetime import date, timedelta
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.sql import SQL, Identifier

from app.config import Settings
from app.models import (
    Lease,
    LeaseReminderCandidate,
    Notification,
    NotificationContact,
    Property,
    ReminderScanResult,
)


class Database:
    def __init__(self, settings: Settings) -> None:
        self._dsn = settings.db_dsn()

    def create_notification_contact(
        self,
        tenant_id: str,
        actor_user_id: str,
        email: str,
        enabled: bool = True,
    ) -> NotificationContact:
        normalized_email = _normalize_notification_contact_email(email)
        if not normalized_email:
            raise ValueError("Notification contact email must not be empty.")

        contact_sql = """
            INSERT INTO notification_contacts (tenant_id, email, enabled)
            VALUES (%s, %s, %s)
            RETURNING contact_id, tenant_id, email, enabled, created_at
        """
        audit_sql = """
            INSERT INTO audit_logs (
                tenant_id, actor_user_id, action, entity_type, entity_id, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
        """
        try:
            with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
                with conn.transaction():
                    contact_row = conn.execute(
                        contact_sql,
                        (tenant_id, normalized_email, enabled),
                    ).fetchone()
                    if not contact_row:
                        raise RuntimeError("Failed to create notification contact.")
                    conn.execute(
                        audit_sql,
                        (
                            tenant_id,
                            actor_user_id,
                            "notification_contact.create",
                            "notification_contact",
                            contact_row["contact_id"],
                            json.dumps({"source": "api", "enabled": enabled}),
                        ),
                    )
        except psycopg.errors.UniqueViolation as exc:
            raise ValueError("Notification contact already exists for tenant.") from exc

        return self._row_to_notification_contact(contact_row)

    def list_notification_contacts(
        self,
        tenant_id: str,
        enabled_only: bool = False,
    ) -> list[NotificationContact]:
        sql = """
            SELECT contact_id, tenant_id, email, enabled, created_at
            FROM notification_contacts
            WHERE tenant_id = %s
        """
        params: tuple[object, ...]
        if enabled_only:
            sql += """
              AND enabled = true
            """
        sql += """
            ORDER BY created_at DESC, contact_id DESC
        """
        params = (tenant_id,)

        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_notification_contact(row) for row in rows]

    def set_notification_contact_enabled(
        self,
        tenant_id: str,
        actor_user_id: str,
        contact_id: UUID,
        enabled: bool,
    ) -> NotificationContact:
        contact_sql = """
            UPDATE notification_contacts
            SET enabled = %s
            WHERE tenant_id = %s AND contact_id = %s
            RETURNING contact_id, tenant_id, email, enabled, created_at
        """
        audit_sql = """
            INSERT INTO audit_logs (
                tenant_id, actor_user_id, action, entity_type, entity_id, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
        """
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            with conn.transaction():
                contact_row = conn.execute(
                    contact_sql,
                    (enabled, tenant_id, contact_id),
                ).fetchone()
                if contact_row is None:
                    raise LookupError("Notification contact not found for tenant.")
                conn.execute(
                    audit_sql,
                    (
                        tenant_id,
                        actor_user_id,
                        "notification_contact.update",
                        "notification_contact",
                        contact_id,
                        json.dumps({"source": "api", "enabled": enabled}),
                    ),
                )

        return self._row_to_notification_contact(contact_row)

    def create_due_lease_reminder_notifications(
        self,
        tenant_id: str | None,
        as_of_date: date,
        days: int,
    ) -> ReminderScanResult:
        candidates = self._list_due_lease_reminders(
            tenant_id=tenant_id,
            as_of_date=as_of_date,
            days=days,
        )
        insert_sql = """
            INSERT INTO notifications (
                tenant_id,
                lease_id,
                type,
                title,
                message,
                due_date
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT ON CONSTRAINT uq_notifications_tenant_lease_type_due_date
            DO NOTHING
            RETURNING notification_id
        """

        created_count = 0
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            with conn.transaction():
                for candidate in candidates:
                    created_row = conn.execute(
                        insert_sql,
                        (
                            candidate.tenant_id,
                            candidate.lease_id,
                            "rent_due_soon",
                            "Rent due soon",
                            _rent_due_soon_message(candidate.days_until_due),
                            candidate.due_date,
                        ),
                    ).fetchone()
                    if created_row:
                        created_count += 1

        return ReminderScanResult(
            tenant_id=tenant_id,
            as_of_date=as_of_date,
            days=days,
            tenant_count=1 if tenant_id else len({item.tenant_id for item in candidates}),
            candidate_count=len(candidates),
            created_count=created_count,
            duplicate_count=len(candidates) - created_count,
        )

    def list_notifications(self, tenant_id: str) -> list[Notification]:
        sql = """
            SELECT
                notification_id,
                tenant_id,
                lease_id,
                type,
                title,
                message,
                due_date,
                created_at,
                read_at
            FROM notifications
            WHERE tenant_id = %s
            ORDER BY created_at DESC
        """
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            rows = conn.execute(sql, (tenant_id,)).fetchall()
        return [self._row_to_notification(row) for row in rows]

    def mark_notification_read(
        self,
        tenant_id: str,
        notification_id: UUID,
    ) -> Notification:
        sql = """
            UPDATE notifications
            SET read_at = COALESCE(read_at, now())
            WHERE tenant_id = %s AND notification_id = %s
            RETURNING
                notification_id,
                tenant_id,
                lease_id,
                type,
                title,
                message,
                due_date,
                created_at,
                read_at
        """
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            with conn.transaction():
                row = conn.execute(sql, (tenant_id, notification_id)).fetchone()

        if row is None:
            raise LookupError("Notification not found for tenant.")

        return self._row_to_notification(row)

    def list_due_lease_reminders(
        self,
        tenant_id: str,
        as_of_date: date,
        days: int,
    ) -> list[LeaseReminderCandidate]:
        return self._list_due_lease_reminders(
            tenant_id=tenant_id,
            as_of_date=as_of_date,
            days=days,
        )

    def _list_due_lease_reminders(
        self,
        tenant_id: str | None,
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
            WHERE rent_due_day_of_month IS NOT NULL
              AND start_date <= %s
              AND end_date >= %s
        """
        params: tuple[object, ...]
        if tenant_id:
            sql += """
              AND tenant_id = %s
            ORDER BY created_at DESC
            """
            params = (range_end, as_of_date, tenant_id)
        else:
            sql += """
            ORDER BY tenant_id, created_at DESC
            """
            params = (range_end, as_of_date)
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            rows = conn.execute(sql, params).fetchall()

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

    def update_lease(
        self,
        tenant_id: str,
        actor_user_id: str,
        lease_id: UUID,
        updates: dict[str, object],
    ) -> Lease:
        lease_sql = """
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
            WHERE tenant_id = %s AND lease_id = %s
            FOR UPDATE
        """
        delete_notifications_sql = """
            DELETE FROM notifications
            WHERE tenant_id = %s
              AND lease_id = %s
              AND type = 'rent_due_soon'
              AND read_at IS NULL
              AND due_date >= %s
        """
        audit_sql = """
            INSERT INTO audit_logs (
                tenant_id, actor_user_id, action, entity_type, entity_id, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
        """
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            with conn.transaction():
                lease_row = conn.execute(lease_sql, (tenant_id, lease_id)).fetchone()
                if lease_row is None:
                    raise LookupError("Lease not found for tenant.")

                start_date = updates.get("start_date", lease_row["start_date"])
                end_date = updates.get("end_date", lease_row["end_date"])
                if end_date < start_date:
                    raise ValueError("'end_date' must be on or after 'start_date'.")

                changed_fields = [
                    field
                    for field in (
                        "resident_name",
                        "rent_due_day_of_month",
                        "start_date",
                        "end_date",
                    )
                    if field in updates and updates[field] != lease_row[field]
                ]
                if not changed_fields:
                    return self._row_to_lease(lease_row)

                assignments = SQL(", ").join(
                    SQL("{} = %s").format(Identifier(field)) for field in changed_fields
                )
                update_sql = SQL("""
                    UPDATE leases
                    SET {assignments}
                    WHERE tenant_id = %s AND lease_id = %s
                    RETURNING
                        lease_id,
                        tenant_id,
                        property_id,
                        resident_name,
                        rent_due_day_of_month,
                        start_date,
                        end_date,
                        created_at
                """).format(assignments=assignments)
                update_params = tuple(updates[field] for field in changed_fields) + (
                    tenant_id,
                    lease_id,
                )
                lease_row = conn.execute(update_sql, update_params).fetchone()

                reminder_fields_changed = any(
                    field in {"rent_due_day_of_month", "start_date", "end_date"}
                    for field in changed_fields
                )
                deleted_notification_count = 0
                if reminder_fields_changed:
                    deleted_notification_count = (
                        conn.execute(
                            delete_notifications_sql,
                            (tenant_id, lease_id, date.today()),
                        ).rowcount
                        or 0
                    )

                conn.execute(
                    audit_sql,
                    (
                        tenant_id,
                        actor_user_id,
                        "lease.update",
                        "lease",
                        lease_id,
                        json.dumps(
                            {
                                "source": "api",
                                "changed_fields": changed_fields,
                                "deleted_notification_count": deleted_notification_count,
                            }
                        ),
                    ),
                )

        if lease_row is None:
            raise RuntimeError("Failed to update lease.")

        return self._row_to_lease(lease_row)

    def update_property(
        self,
        tenant_id: str,
        actor_user_id: str,
        property_id: UUID,
        updates: dict[str, str],
    ) -> Property:
        property_sql = """
            SELECT property_id, tenant_id, name, address, created_at
            FROM properties
            WHERE tenant_id = %s AND property_id = %s
            FOR UPDATE
        """
        audit_sql = """
            INSERT INTO audit_logs (
                tenant_id, actor_user_id, action, entity_type, entity_id, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
        """
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            with conn.transaction():
                property_row = conn.execute(property_sql, (tenant_id, property_id)).fetchone()
                if property_row is None:
                    raise LookupError("Property not found for tenant.")

                changed_fields = [
                    field
                    for field in ("name", "address")
                    if field in updates and updates[field] != property_row[field]
                ]
                if not changed_fields:
                    return self._row_to_property(property_row)

                assignments = SQL(", ").join(
                    SQL("{} = %s").format(Identifier(field)) for field in changed_fields
                )
                update_sql = SQL("""
                    UPDATE properties
                    SET {assignments}
                    WHERE tenant_id = %s AND property_id = %s
                    RETURNING property_id, tenant_id, name, address, created_at
                """).format(assignments=assignments)
                update_params = tuple(updates[field] for field in changed_fields) + (
                    tenant_id,
                    property_id,
                )
                property_row = conn.execute(update_sql, update_params).fetchone()
                conn.execute(
                    audit_sql,
                    (
                        tenant_id,
                        actor_user_id,
                        "property.update",
                        "property",
                        property_id,
                        json.dumps({"source": "api", "changed_fields": changed_fields}),
                    ),
                )

        if property_row is None:
            raise RuntimeError("Failed to update property.")

        return self._row_to_property(property_row)

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

    @staticmethod
    def _row_to_notification(row: dict[str, Any]) -> Notification:
        return Notification(
            notification_id=row["notification_id"],
            tenant_id=row["tenant_id"],
            lease_id=row["lease_id"],
            type=row["type"],
            title=row["title"],
            message=row["message"],
            due_date=row["due_date"],
            created_at=row["created_at"],
            read_at=row["read_at"],
        )

    @staticmethod
    def _row_to_notification_contact(row: dict[str, Any]) -> NotificationContact:
        return NotificationContact(
            contact_id=row["contact_id"],
            tenant_id=row["tenant_id"],
            email=row["email"],
            enabled=row["enabled"],
            created_at=row["created_at"],
        )


def notification_to_dict(item: Notification) -> dict[str, Any]:
    return {
        "notification_id": str(item.notification_id),
        "tenant_id": item.tenant_id,
        "lease_id": str(item.lease_id),
        "type": item.type,
        "title": item.title,
        "message": item.message,
        "due_date": item.due_date.isoformat(),
        "created_at": item.created_at.isoformat(),
        "read_at": item.read_at.isoformat() if item.read_at else None,
    }


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


def notifications_to_dict(items: Sequence[Notification]) -> list[dict[str, Any]]:
    return [notification_to_dict(item) for item in items]


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


def _rent_due_soon_message(days_until_due: int) -> str:
    if days_until_due == 1:
        return "Rent is due in 1 day."
    return f"Rent is due in {days_until_due} days."


def _normalize_notification_contact_email(email: str) -> str:
    return email.strip().lower()
