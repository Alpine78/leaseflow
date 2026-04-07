from __future__ import annotations

import os
from datetime import date
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row
from psycopg.sql import SQL, Identifier, Literal

from app.config import Settings, load_settings
from app.db import Database


def _integration_enabled() -> bool:
    return os.getenv("LEASEFLOW_RUN_DB_INTEGRATION") == "1"


@pytest.fixture
def integration_settings() -> Settings:
    if not _integration_enabled():
        pytest.skip("Local DB integration test. Run via make test-integration-local.")

    load_settings.cache_clear()
    settings = load_settings()
    yield settings
    load_settings.cache_clear()


def _cleanup_test_tenant(settings: Settings, tenant_id: str) -> None:
    with psycopg.connect(settings.db_dsn(), row_factory=dict_row) as conn:
        with conn.transaction():
            conn.execute("DELETE FROM notifications WHERE tenant_id = %s", (tenant_id,))
            conn.execute("DELETE FROM audit_logs WHERE tenant_id = %s", (tenant_id,))
            conn.execute("DELETE FROM leases WHERE tenant_id = %s", (tenant_id,))
            conn.execute("DELETE FROM properties WHERE tenant_id = %s", (tenant_id,))


def test_create_property_writes_property_and_audit_log(integration_settings: Settings) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"
    name = f"Integration HQ {uuid4().hex[:8]}"
    address = f"Audit Street {uuid4().hex[:8]}"

    try:
        created = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=name,
            address=address,
        )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            property_rows = conn.execute(
                """
                SELECT property_id, tenant_id, name, address
                FROM properties
                WHERE tenant_id = %s AND property_id = %s
                """,
                (tenant_id, created.property_id),
            ).fetchall()
            audit_rows = conn.execute(
                """
                SELECT tenant_id, actor_user_id, action, entity_type, entity_id, metadata
                FROM audit_logs
                WHERE tenant_id = %s AND entity_id = %s
                """,
                (tenant_id, created.property_id),
            ).fetchall()

        assert len(property_rows) == 1
        assert property_rows[0]["tenant_id"] == tenant_id
        assert property_rows[0]["name"] == name
        assert property_rows[0]["address"] == address

        assert len(audit_rows) == 1
        assert audit_rows[0]["tenant_id"] == tenant_id
        assert audit_rows[0]["actor_user_id"] == actor_user_id
        assert audit_rows[0]["action"] == "property.create"
        assert audit_rows[0]["entity_type"] == "property"
        assert audit_rows[0]["entity_id"] == created.property_id
        assert audit_rows[0]["metadata"] == {"source": "api"}
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_create_property_rolls_back_when_audit_log_write_fails(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"
    name = f"Rollback HQ {uuid4().hex[:8]}"
    address = f"Rollback Street {uuid4().hex[:8]}"
    constraint_name = f"audit_logs_reject_{uuid4().hex[:12]}"

    try:
        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            with conn.transaction():
                conn.execute(
                    SQL(
                        """
                        ALTER TABLE audit_logs
                        ADD CONSTRAINT {constraint_name}
                        CHECK (tenant_id <> {tenant_id})
                        """
                    ).format(
                        constraint_name=Identifier(constraint_name),
                        tenant_id=Literal(tenant_id),
                    )
                )

        with pytest.raises(psycopg.Error):
            db.create_property(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                name=name,
                address=address,
            )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            property_rows = conn.execute(
                """
                SELECT property_id
                FROM properties
                WHERE tenant_id = %s
                """,
                (tenant_id,),
            ).fetchall()
            audit_rows = conn.execute(
                """
                SELECT audit_id
                FROM audit_logs
                WHERE tenant_id = %s
                """,
                (tenant_id,),
            ).fetchall()

        assert property_rows == []
        assert audit_rows == []
    finally:
        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            with conn.transaction():
                conn.execute(
                    SQL(
                        "ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS {constraint_name}"
                    ).format(constraint_name=Identifier(constraint_name))
                )
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_list_properties_returns_only_requested_tenant_rows(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    other_tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"
    other_actor_user_id = f"user-{uuid4().hex[:12]}"
    name = f"Tenant HQ {uuid4().hex[:8]}"
    address = f"Tenant Street {uuid4().hex[:8]}"

    try:
        created = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=name,
            address=address,
        )
        db.create_property(
            tenant_id=other_tenant_id,
            actor_user_id=other_actor_user_id,
            name=f"Other HQ {uuid4().hex[:8]}",
            address=f"Other Street {uuid4().hex[:8]}",
        )

        listed = db.list_properties(tenant_id=tenant_id)

        assert len(listed) == 1
        assert listed[0].property_id == created.property_id
        assert listed[0].tenant_id == tenant_id
        assert listed[0].name == name
        assert listed[0].address == address
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)
        _cleanup_test_tenant(integration_settings, other_tenant_id)


def test_create_lease_writes_lease_and_audit_log(integration_settings: Settings) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"
    resident_name = f"Alice {uuid4().hex[:8]}"
    rent_due_day_of_month = 5
    start_date = date(2026, 5, 1)
    end_date = date(2027, 4, 30)

    try:
        property_record = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=f"Lease HQ {uuid4().hex[:8]}",
            address=f"Lease Street {uuid4().hex[:8]}",
        )
        created = db.create_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name=resident_name,
            rent_due_day_of_month=rent_due_day_of_month,
            start_date=start_date,
            end_date=end_date,
        )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            lease_rows = conn.execute(
                """
                SELECT
                    lease_id,
                    tenant_id,
                    property_id,
                    resident_name,
                    rent_due_day_of_month,
                    start_date,
                    end_date
                FROM leases
                WHERE tenant_id = %s AND lease_id = %s
                """,
                (tenant_id, created.lease_id),
            ).fetchall()
            audit_rows = conn.execute(
                """
                SELECT tenant_id, actor_user_id, action, entity_type, entity_id, metadata
                FROM audit_logs
                WHERE tenant_id = %s AND entity_id = %s
                """,
                (tenant_id, created.lease_id),
            ).fetchall()

        assert len(lease_rows) == 1
        assert lease_rows[0]["tenant_id"] == tenant_id
        assert lease_rows[0]["property_id"] == property_record.property_id
        assert lease_rows[0]["resident_name"] == resident_name
        assert lease_rows[0]["rent_due_day_of_month"] == rent_due_day_of_month
        assert lease_rows[0]["start_date"] == start_date
        assert lease_rows[0]["end_date"] == end_date

        assert len(audit_rows) == 1
        assert audit_rows[0]["tenant_id"] == tenant_id
        assert audit_rows[0]["actor_user_id"] == actor_user_id
        assert audit_rows[0]["action"] == "lease.create"
        assert audit_rows[0]["entity_type"] == "lease"
        assert audit_rows[0]["entity_id"] == created.lease_id
        assert audit_rows[0]["metadata"] == {"source": "api"}
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_create_lease_rejects_cross_tenant_property_reference(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    other_tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"

    try:
        other_property = db.create_property(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            name=f"Other HQ {uuid4().hex[:8]}",
            address=f"Other Street {uuid4().hex[:8]}",
        )

        with pytest.raises(ValueError, match="Property not found for tenant."):
            db.create_lease(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                property_id=other_property.property_id,
                resident_name=f"Bob {uuid4().hex[:8]}",
                rent_due_day_of_month=5,
                start_date=date(2026, 5, 1),
                end_date=date(2027, 4, 30),
            )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            lease_rows = conn.execute(
                """
                SELECT lease_id
                FROM leases
                WHERE tenant_id IN (%s, %s)
                """,
                (tenant_id, other_tenant_id),
            ).fetchall()
            audit_rows = conn.execute(
                """
                SELECT audit_id
                FROM audit_logs
                WHERE tenant_id = %s AND action = 'lease.create'
                """,
                (tenant_id,),
            ).fetchall()

        assert lease_rows == []
        assert audit_rows == []
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)
        _cleanup_test_tenant(integration_settings, other_tenant_id)


def test_create_lease_rolls_back_when_audit_log_write_fails(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"
    constraint_name = f"audit_logs_reject_{uuid4().hex[:12]}"

    try:
        property_record = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=f"Rollback HQ {uuid4().hex[:8]}",
            address=f"Rollback Street {uuid4().hex[:8]}",
        )
        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            with conn.transaction():
                conn.execute(
                    SQL(
                        """
                        ALTER TABLE audit_logs
                        ADD CONSTRAINT {constraint_name}
                        CHECK (action <> 'lease.create' OR tenant_id <> {tenant_id})
                        """
                    ).format(
                        constraint_name=Identifier(constraint_name),
                        tenant_id=Literal(tenant_id),
                    )
                )

        with pytest.raises(psycopg.Error):
            db.create_lease(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                property_id=property_record.property_id,
                resident_name=f"Carol {uuid4().hex[:8]}",
                rent_due_day_of_month=5,
                start_date=date(2026, 5, 1),
                end_date=date(2027, 4, 30),
            )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            lease_rows = conn.execute(
                """
                SELECT lease_id
                FROM leases
                WHERE tenant_id = %s
                """,
                (tenant_id,),
            ).fetchall()
            audit_rows = conn.execute(
                """
                SELECT audit_id
                FROM audit_logs
                WHERE tenant_id = %s AND action = 'lease.create'
                """,
                (tenant_id,),
            ).fetchall()

        assert lease_rows == []
        assert audit_rows == []
    finally:
        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            with conn.transaction():
                conn.execute(
                    SQL(
                        "ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS {constraint_name}"
                    ).format(constraint_name=Identifier(constraint_name))
                )
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_list_leases_returns_only_requested_tenant_rows(integration_settings: Settings) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    other_tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"

    try:
        property_record = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=f"Lease HQ {uuid4().hex[:8]}",
            address=f"Lease Street {uuid4().hex[:8]}",
        )
        other_property = db.create_property(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            name=f"Other Lease HQ {uuid4().hex[:8]}",
            address=f"Other Lease Street {uuid4().hex[:8]}",
        )
        created = db.create_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name=f"Dana {uuid4().hex[:8]}",
            rent_due_day_of_month=5,
            start_date=date(2026, 5, 1),
            end_date=date(2027, 4, 30),
        )
        db.create_lease(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            property_id=other_property.property_id,
            resident_name=f"Eve {uuid4().hex[:8]}",
            rent_due_day_of_month=7,
            start_date=date(2026, 6, 1),
            end_date=date(2027, 5, 31),
        )

        listed = db.list_leases(tenant_id=tenant_id)

        assert len(listed) == 1
        assert listed[0].lease_id == created.lease_id
        assert listed[0].tenant_id == tenant_id
        assert listed[0].property_id == property_record.property_id
        assert listed[0].rent_due_day_of_month == 5
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)
        _cleanup_test_tenant(integration_settings, other_tenant_id)


def test_list_due_lease_reminders_returns_only_due_active_tenant_leases(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    other_tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"
    as_of_date = date(2026, 4, 3)

    try:
        property_record = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=f"Reminder HQ {uuid4().hex[:8]}",
            address=f"Reminder Street {uuid4().hex[:8]}",
        )
        other_property = db.create_property(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            name=f"Other Reminder HQ {uuid4().hex[:8]}",
            address=f"Other Reminder Street {uuid4().hex[:8]}",
        )

        due_soon = db.create_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name=f"Due Soon {uuid4().hex[:8]}",
            rent_due_day_of_month=5,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        db.create_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name=f"Too Late {uuid4().hex[:8]}",
            rent_due_day_of_month=20,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        db.create_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name=f"Inactive {uuid4().hex[:8]}",
            rent_due_day_of_month=4,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 4, 2),
        )
        db.create_lease(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            property_id=other_property.property_id,
            resident_name=f"Other Tenant {uuid4().hex[:8]}",
            rent_due_day_of_month=5,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        listed = db.list_due_lease_reminders(
            tenant_id=tenant_id,
            as_of_date=as_of_date,
            days=7,
        )

        assert len(listed) == 1
        assert listed[0].lease_id == due_soon.lease_id
        assert listed[0].tenant_id == tenant_id
        assert listed[0].property_id == property_record.property_id
        assert listed[0].resident_name == due_soon.resident_name
        assert listed[0].rent_due_day_of_month == 5
        assert listed[0].due_date == date(2026, 4, 5)
        assert listed[0].days_until_due == 2
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)
        _cleanup_test_tenant(integration_settings, other_tenant_id)


def test_list_notifications_returns_only_requested_tenant_rows(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    other_tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"

    try:
        property_record = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=f"Notification HQ {uuid4().hex[:8]}",
            address=f"Notification Street {uuid4().hex[:8]}",
        )
        other_property = db.create_property(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            name=f"Other Notification HQ {uuid4().hex[:8]}",
            address=f"Other Notification Street {uuid4().hex[:8]}",
        )
        lease_record = db.create_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name=f"Reminder User {uuid4().hex[:8]}",
            rent_due_day_of_month=5,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        other_lease = db.create_lease(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            property_id=other_property.property_id,
            resident_name=f"Other Reminder User {uuid4().hex[:8]}",
            rent_due_day_of_month=7,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            with conn.transaction():
                conn.execute(
                    """
                    INSERT INTO notifications (
                        tenant_id,
                        lease_id,
                        type,
                        title,
                        message,
                        due_date
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        tenant_id,
                        lease_record.lease_id,
                        "rent_due_soon",
                        "Rent due soon",
                        "Rent is due in 2 days.",
                        date(2026, 4, 5),
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO notifications (
                        tenant_id,
                        lease_id,
                        type,
                        title,
                        message,
                        due_date
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        other_tenant_id,
                        other_lease.lease_id,
                        "rent_due_soon",
                        "Other rent due soon",
                        "Other rent is due in 1 day.",
                        date(2026, 4, 4),
                    ),
                )

        listed = db.list_notifications(tenant_id=tenant_id)

        assert len(listed) == 1
        assert listed[0].tenant_id == tenant_id
        assert listed[0].lease_id == lease_record.lease_id
        assert listed[0].type == "rent_due_soon"
        assert listed[0].title == "Rent due soon"
        assert listed[0].message == "Rent is due in 2 days."
        assert listed[0].due_date == date(2026, 4, 5)
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)
        _cleanup_test_tenant(integration_settings, other_tenant_id)


def test_create_due_lease_reminder_notifications_is_idempotent(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"
    as_of_date = date(2026, 4, 3)

    try:
        property_record = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=f"Scan HQ {uuid4().hex[:8]}",
            address=f"Scan Street {uuid4().hex[:8]}",
        )
        lease_record = db.create_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name=f"Reminder Scan User {uuid4().hex[:8]}",
            rent_due_day_of_month=5,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        first_run = db.create_due_lease_reminder_notifications(
            tenant_id=tenant_id,
            as_of_date=as_of_date,
            days=7,
        )
        second_run = db.create_due_lease_reminder_notifications(
            tenant_id=tenant_id,
            as_of_date=as_of_date,
            days=7,
        )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            rows = conn.execute(
                """
                SELECT tenant_id, lease_id, type, title, message, due_date
                FROM notifications
                WHERE tenant_id = %s
                ORDER BY created_at DESC
                """,
                (tenant_id,),
            ).fetchall()

        assert first_run.tenant_id == tenant_id
        assert first_run.as_of_date == as_of_date
        assert first_run.days == 7
        assert first_run.tenant_count == 1
        assert first_run.candidate_count == 1
        assert first_run.created_count == 1
        assert first_run.duplicate_count == 0

        assert second_run.candidate_count == 1
        assert second_run.created_count == 0
        assert second_run.duplicate_count == 1

        assert len(rows) == 1
        assert rows[0]["tenant_id"] == tenant_id
        assert rows[0]["lease_id"] == lease_record.lease_id
        assert rows[0]["type"] == "rent_due_soon"
        assert rows[0]["title"] == "Rent due soon"
        assert rows[0]["message"] == "Rent is due in 2 days."
        assert rows[0]["due_date"] == date(2026, 4, 5)
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_create_due_lease_reminder_notifications_scans_all_tenants_when_unscoped(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    other_tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"
    as_of_date = date(2026, 4, 3)

    try:
        property_record = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=f"Global Scan HQ {uuid4().hex[:8]}",
            address=f"Global Scan Street {uuid4().hex[:8]}",
        )
        other_property = db.create_property(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            name=f"Other Global Scan HQ {uuid4().hex[:8]}",
            address=f"Other Global Scan Street {uuid4().hex[:8]}",
        )
        lease_record = db.create_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name=f"Global Scan User {uuid4().hex[:8]}",
            rent_due_day_of_month=5,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        other_lease = db.create_lease(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            property_id=other_property.property_id,
            resident_name=f"Other Global Scan User {uuid4().hex[:8]}",
            rent_due_day_of_month=6,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        result = db.create_due_lease_reminder_notifications(
            tenant_id=None,
            as_of_date=as_of_date,
            days=7,
        )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            rows = conn.execute(
                """
                SELECT tenant_id, lease_id, type, due_date
                FROM notifications
                WHERE tenant_id IN (%s, %s)
                ORDER BY tenant_id, due_date
                """,
                (tenant_id, other_tenant_id),
            ).fetchall()

        assert result.tenant_id is None
        assert result.tenant_count >= 2
        assert result.candidate_count >= 2
        assert result.created_count >= 2
        assert result.duplicate_count >= 0

        assert len(rows) == 2
        assert {
            (row["tenant_id"], row["lease_id"], row["type"], row["due_date"])
            for row in rows
        } == {
            (tenant_id, lease_record.lease_id, "rent_due_soon", date(2026, 4, 5)),
            (other_tenant_id, other_lease.lease_id, "rent_due_soon", date(2026, 4, 6)),
        }
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)
        _cleanup_test_tenant(integration_settings, other_tenant_id)
