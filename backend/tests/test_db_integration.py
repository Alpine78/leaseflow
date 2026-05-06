from __future__ import annotations

import os
from datetime import date, timedelta
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row
from psycopg.sql import SQL, Identifier, Literal

from app.config import Settings, load_settings
from app.db import Database, notification_to_dict


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
            conn.execute(
                "DELETE FROM notification_email_deliveries WHERE tenant_id = %s",
                (tenant_id,),
            )
            conn.execute("DELETE FROM notifications WHERE tenant_id = %s", (tenant_id,))
            conn.execute("DELETE FROM notification_contacts WHERE tenant_id = %s", (tenant_id,))
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


def test_update_property_writes_property_change_and_audit_log(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"

    try:
        created = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=f"Original HQ {uuid4().hex[:8]}",
            address=f"Original Street {uuid4().hex[:8]}",
        )

        updated = db.update_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=created.property_id,
            updates={"name": "Updated HQ", "address": "Updated Street 2"},
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
                WHERE tenant_id = %s AND entity_id = %s AND action = 'property.update'
                """,
                (tenant_id, created.property_id),
            ).fetchall()

        assert updated.property_id == created.property_id
        assert updated.tenant_id == tenant_id
        assert updated.name == "Updated HQ"
        assert updated.address == "Updated Street 2"

        assert len(property_rows) == 1
        assert property_rows[0]["name"] == "Updated HQ"
        assert property_rows[0]["address"] == "Updated Street 2"

        assert len(audit_rows) == 1
        assert audit_rows[0]["tenant_id"] == tenant_id
        assert audit_rows[0]["actor_user_id"] == actor_user_id
        assert audit_rows[0]["action"] == "property.update"
        assert audit_rows[0]["entity_type"] == "property"
        assert audit_rows[0]["entity_id"] == created.property_id
        assert audit_rows[0]["metadata"] == {
            "source": "api",
            "changed_fields": ["name", "address"],
        }
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_update_property_rejects_cross_tenant_access(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    other_tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"

    try:
        created = db.create_property(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            name=f"Other HQ {uuid4().hex[:8]}",
            address=f"Other Street {uuid4().hex[:8]}",
        )

        with pytest.raises(LookupError, match="Property not found for tenant."):
            db.update_property(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                property_id=created.property_id,
                updates={"name": "Updated HQ"},
            )
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)
        _cleanup_test_tenant(integration_settings, other_tenant_id)


def test_update_property_is_idempotent_when_values_are_unchanged(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"
    name = f"Stable HQ {uuid4().hex[:8]}"
    address = f"Stable Street {uuid4().hex[:8]}"

    try:
        created = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=name,
            address=address,
        )

        updated = db.update_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=created.property_id,
            updates={"name": name, "address": address},
        )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            property_rows = conn.execute(
                """
                SELECT property_id, name, address
                FROM properties
                WHERE tenant_id = %s AND property_id = %s
                """,
                (tenant_id, created.property_id),
            ).fetchall()
            audit_rows = conn.execute(
                """
                SELECT audit_id
                FROM audit_logs
                WHERE tenant_id = %s AND entity_id = %s AND action = 'property.update'
                """,
                (tenant_id, created.property_id),
            ).fetchall()

        assert updated.property_id == created.property_id
        assert updated.name == name
        assert updated.address == address
        assert len(property_rows) == 1
        assert property_rows[0]["name"] == name
        assert property_rows[0]["address"] == address
        assert audit_rows == []
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_update_property_rolls_back_when_audit_log_write_fails(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"
    constraint_name = f"audit_logs_reject_{uuid4().hex[:12]}"

    try:
        created = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=f"Rollback Update HQ {uuid4().hex[:8]}",
            address=f"Rollback Update Street {uuid4().hex[:8]}",
        )
        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            with conn.transaction():
                conn.execute(
                    SQL(
                        """
                        ALTER TABLE audit_logs
                        ADD CONSTRAINT {constraint_name}
                        CHECK (action <> 'property.update' OR tenant_id <> {tenant_id})
                        """
                    ).format(
                        constraint_name=Identifier(constraint_name),
                        tenant_id=Literal(tenant_id),
                    )
                )

        with pytest.raises(psycopg.Error):
            db.update_property(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                property_id=created.property_id,
                updates={"name": "Broken Update"},
            )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            property_rows = conn.execute(
                """
                SELECT property_id, name, address
                FROM properties
                WHERE tenant_id = %s AND property_id = %s
                """,
                (tenant_id, created.property_id),
            ).fetchall()
            audit_rows = conn.execute(
                """
                SELECT audit_id
                FROM audit_logs
                WHERE tenant_id = %s AND entity_id = %s AND action = 'property.update'
                """,
                (tenant_id, created.property_id),
            ).fetchall()

        assert len(property_rows) == 1
        assert property_rows[0]["name"] == created.name
        assert property_rows[0]["address"] == created.address
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


def test_update_lease_writes_change_audit_and_deletes_future_unread_reminders(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"
    today = date.today()
    next_year = today.replace(year=today.year + 1)

    try:
        property_record = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=f"Lease Update HQ {uuid4().hex[:8]}",
            address=f"Lease Update Street {uuid4().hex[:8]}",
        )
        created = db.create_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name=f"Original Resident {uuid4().hex[:8]}",
            rent_due_day_of_month=5,
            start_date=today,
            end_date=next_year,
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
                        created.lease_id,
                        "rent_due_soon",
                        "Rent due soon",
                        "Rent is due soon.",
                        today,
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
                        due_date,
                        read_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, now())
                    """,
                    (
                        tenant_id,
                        created.lease_id,
                        "rent_due_soon",
                        "Read reminder",
                        "Already read.",
                        today + timedelta(days=1),
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
                        tenant_id,
                        created.lease_id,
                        "rent_due_soon",
                        "Past reminder",
                        "Past due reminder.",
                        today - timedelta(days=1),
                    ),
                )

        updated = db.update_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            lease_id=created.lease_id,
            updates={
                "rent_due_day_of_month": 9,
                "start_date": today + timedelta(days=2),
                "end_date": next_year,
            },
        )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            lease_rows = conn.execute(
                """
                SELECT resident_name, rent_due_day_of_month, start_date, end_date
                FROM leases
                WHERE tenant_id = %s AND lease_id = %s
                """,
                (tenant_id, created.lease_id),
            ).fetchall()
            audit_rows = conn.execute(
                """
                SELECT metadata
                FROM audit_logs
                WHERE tenant_id = %s AND entity_id = %s AND action = 'lease.update'
                """,
                (tenant_id, created.lease_id),
            ).fetchall()
            notification_rows = conn.execute(
                """
                SELECT title, due_date, read_at
                FROM notifications
                WHERE tenant_id = %s AND lease_id = %s
                ORDER BY due_date
                """,
                (tenant_id, created.lease_id),
            ).fetchall()

        assert updated.lease_id == created.lease_id
        assert updated.rent_due_day_of_month == 9
        assert updated.start_date == today + timedelta(days=2)
        assert len(lease_rows) == 1
        assert lease_rows[0]["rent_due_day_of_month"] == 9
        assert len(audit_rows) == 1
        assert audit_rows[0]["metadata"] == {
            "source": "api",
            "changed_fields": ["rent_due_day_of_month", "start_date"],
            "deleted_notification_count": 1,
        }
        assert len(notification_rows) == 2
        assert notification_rows[0]["title"] == "Past reminder"
        assert notification_rows[1]["title"] == "Read reminder"
        assert notification_rows[1]["read_at"] is not None
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_update_lease_rejects_cross_tenant_access(integration_settings: Settings) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    other_tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"
    today = date.today()
    next_year = today.replace(year=today.year + 1)

    try:
        property_record = db.create_property(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            name=f"Other Lease HQ {uuid4().hex[:8]}",
            address=f"Other Lease Street {uuid4().hex[:8]}",
        )
        created = db.create_lease(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name=f"Other Resident {uuid4().hex[:8]}",
            rent_due_day_of_month=5,
            start_date=today,
            end_date=next_year,
        )

        with pytest.raises(LookupError, match="Lease not found for tenant."):
            db.update_lease(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                lease_id=created.lease_id,
                updates={"resident_name": "Updated Resident"},
            )
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)
        _cleanup_test_tenant(integration_settings, other_tenant_id)


def test_update_lease_is_idempotent_when_values_are_unchanged(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"
    today = date.today()
    next_year = today.replace(year=today.year + 1)

    try:
        property_record = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=f"Stable Lease HQ {uuid4().hex[:8]}",
            address=f"Stable Lease Street {uuid4().hex[:8]}",
        )
        created = db.create_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name="Stable Resident",
            rent_due_day_of_month=5,
            start_date=today,
            end_date=next_year,
        )

        updated = db.update_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            lease_id=created.lease_id,
            updates={
                "resident_name": "Stable Resident",
                "rent_due_day_of_month": 5,
                "start_date": today,
                "end_date": next_year,
            },
        )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            audit_rows = conn.execute(
                """
                SELECT audit_id
                FROM audit_logs
                WHERE tenant_id = %s AND entity_id = %s AND action = 'lease.update'
                """,
                (tenant_id, created.lease_id),
            ).fetchall()

        assert updated.lease_id == created.lease_id
        assert updated.resident_name == "Stable Resident"
        assert audit_rows == []
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_update_lease_resident_name_only_keeps_future_unread_reminders(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"
    today = date.today()
    next_year = today.replace(year=today.year + 1)

    try:
        property_record = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=f"Resident Lease HQ {uuid4().hex[:8]}",
            address=f"Resident Lease Street {uuid4().hex[:8]}",
        )
        created = db.create_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name="Original Resident",
            rent_due_day_of_month=5,
            start_date=today,
            end_date=next_year,
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
                        created.lease_id,
                        "rent_due_soon",
                        "Rent due soon",
                        "Rent is due soon.",
                        today + timedelta(days=1),
                    ),
                )

        updated = db.update_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            lease_id=created.lease_id,
            updates={"resident_name": "Updated Resident"},
        )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            audit_rows = conn.execute(
                """
                SELECT metadata
                FROM audit_logs
                WHERE tenant_id = %s AND entity_id = %s AND action = 'lease.update'
                """,
                (tenant_id, created.lease_id),
            ).fetchall()
            notification_rows = conn.execute(
                """
                SELECT notification_id
                FROM notifications
                WHERE tenant_id = %s AND lease_id = %s
                """,
                (tenant_id, created.lease_id),
            ).fetchall()

        assert updated.resident_name == "Updated Resident"
        assert len(notification_rows) == 1
        assert audit_rows[0]["metadata"] == {
            "source": "api",
            "changed_fields": ["resident_name"],
            "deleted_notification_count": 0,
        }
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_update_lease_changes_due_reminder_candidates(integration_settings: Settings) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"
    as_of_date = date(2026, 4, 3)
    original_due_day = 20
    updated_due_day = 5

    try:
        property_record = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=f"Reminder Candidate HQ {uuid4().hex[:8]}",
            address=f"Reminder Candidate Street {uuid4().hex[:8]}",
        )
        created = db.create_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name="Reminder Candidate Resident",
            rent_due_day_of_month=original_due_day,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        before = db.list_due_lease_reminders(
            tenant_id=tenant_id,
            as_of_date=as_of_date,
            days=7,
        )

        db.update_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            lease_id=created.lease_id,
            updates={"rent_due_day_of_month": updated_due_day},
        )

        after = db.list_due_lease_reminders(
            tenant_id=tenant_id,
            as_of_date=as_of_date,
            days=7,
        )

        assert before == []
        assert len(after) == 1
        assert after[0].lease_id == created.lease_id
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_update_lease_rolls_back_when_audit_log_write_fails(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"
    constraint_name = f"audit_logs_reject_{uuid4().hex[:12]}"
    today = date.today()
    next_year = today.replace(year=today.year + 1)

    try:
        property_record = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=f"Rollback Lease HQ {uuid4().hex[:8]}",
            address=f"Rollback Lease Street {uuid4().hex[:8]}",
        )
        created = db.create_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name="Rollback Resident",
            rent_due_day_of_month=5,
            start_date=today,
            end_date=next_year,
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
                        created.lease_id,
                        "rent_due_soon",
                        "Future unread",
                        "Future unread.",
                        today + timedelta(days=1),
                    ),
                )
                conn.execute(
                    SQL(
                        """
                        ALTER TABLE audit_logs
                        ADD CONSTRAINT {constraint_name}
                        CHECK (action <> 'lease.update' OR tenant_id <> {tenant_id})
                        """
                    ).format(
                        constraint_name=Identifier(constraint_name),
                        tenant_id=Literal(tenant_id),
                    )
                )

        with pytest.raises(psycopg.Error):
            db.update_lease(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                lease_id=created.lease_id,
                updates={"rent_due_day_of_month": 9},
            )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            lease_rows = conn.execute(
                """
                SELECT rent_due_day_of_month
                FROM leases
                WHERE tenant_id = %s AND lease_id = %s
                """,
                (tenant_id, created.lease_id),
            ).fetchall()
            audit_rows = conn.execute(
                """
                SELECT audit_id
                FROM audit_logs
                WHERE tenant_id = %s AND entity_id = %s AND action = 'lease.update'
                """,
                (tenant_id, created.lease_id),
            ).fetchall()
            notification_rows = conn.execute(
                """
                SELECT notification_id
                FROM notifications
                WHERE tenant_id = %s AND lease_id = %s
                """,
                (tenant_id, created.lease_id),
            ).fetchall()

        assert lease_rows[0]["rent_due_day_of_month"] == 5
        assert audit_rows == []
        assert len(notification_rows) == 1
    finally:
        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            with conn.transaction():
                conn.execute(
                    SQL(
                        "ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS {constraint_name}"
                    ).format(constraint_name=Identifier(constraint_name))
                )
        _cleanup_test_tenant(integration_settings, tenant_id)


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
        assert listed[0].read_at is None
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)
        _cleanup_test_tenant(integration_settings, other_tenant_id)


def test_mark_notification_read_sets_timestamp_once_and_is_idempotent(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"

    try:
        property_record = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=f"Read HQ {uuid4().hex[:8]}",
            address=f"Read Street {uuid4().hex[:8]}",
        )
        lease_record = db.create_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name=f"Read User {uuid4().hex[:8]}",
            rent_due_day_of_month=5,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            with conn.transaction():
                notification_id = conn.execute(
                    """
                    INSERT INTO notifications (
                        tenant_id,
                        lease_id,
                        type,
                        title,
                        message,
                        due_date
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING notification_id
                    """,
                    (
                        tenant_id,
                        lease_record.lease_id,
                        "rent_due_soon",
                        "Rent due soon",
                        "Rent is due in 2 days.",
                        date(2026, 4, 5),
                    ),
                ).fetchone()["notification_id"]

        first_read = db.mark_notification_read(
            tenant_id=tenant_id,
            notification_id=notification_id,
        )
        second_read = db.mark_notification_read(
            tenant_id=tenant_id,
            notification_id=notification_id,
        )

        assert first_read.notification_id == notification_id
        assert first_read.read_at is not None
        assert second_read.notification_id == notification_id
        assert second_read.read_at == first_read.read_at
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_mark_notification_read_rejects_cross_tenant_access(
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
            name=f"Other Read HQ {uuid4().hex[:8]}",
            address=f"Other Read Street {uuid4().hex[:8]}",
        )
        other_lease = db.create_lease(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            property_id=other_property.property_id,
            resident_name=f"Other Read User {uuid4().hex[:8]}",
            rent_due_day_of_month=5,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            with conn.transaction():
                notification_id = conn.execute(
                    """
                    INSERT INTO notifications (
                        tenant_id,
                        lease_id,
                        type,
                        title,
                        message,
                        due_date
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING notification_id
                    """,
                    (
                        other_tenant_id,
                        other_lease.lease_id,
                        "rent_due_soon",
                        "Rent due soon",
                        "Rent is due in 2 days.",
                        date(2026, 4, 5),
                    ),
                ).fetchone()["notification_id"]

        with pytest.raises(LookupError, match="Notification not found for tenant."):
            db.mark_notification_read(
                tenant_id=tenant_id,
                notification_id=notification_id,
            )
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)
        _cleanup_test_tenant(integration_settings, other_tenant_id)


def test_create_notification_contact_stores_normalized_email_and_audit_log(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"

    try:
        created = db.create_notification_contact(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            email="  Contact.One+Rent@Example.COM  ",
        )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            contact_rows = conn.execute(
                """
                SELECT contact_id, tenant_id, email, enabled
                FROM notification_contacts
                WHERE tenant_id = %s AND contact_id = %s
                """,
                (tenant_id, created.contact_id),
            ).fetchall()
            audit_rows = conn.execute(
                """
                SELECT tenant_id, actor_user_id, action, entity_type, entity_id, metadata
                FROM audit_logs
                WHERE tenant_id = %s
                  AND entity_id = %s
                  AND action = 'notification_contact.create'
                """,
                (tenant_id, created.contact_id),
            ).fetchall()

        assert created.tenant_id == tenant_id
        assert created.email == "contact.one+rent@example.com"
        assert created.enabled is True

        assert len(contact_rows) == 1
        assert contact_rows[0]["email"] == "contact.one+rent@example.com"
        assert contact_rows[0]["enabled"] is True

        assert len(audit_rows) == 1
        assert audit_rows[0]["tenant_id"] == tenant_id
        assert audit_rows[0]["actor_user_id"] == actor_user_id
        assert audit_rows[0]["entity_type"] == "notification_contact"
        assert audit_rows[0]["entity_id"] == created.contact_id
        assert audit_rows[0]["metadata"] == {"source": "api", "enabled": True}
        assert "email" not in audit_rows[0]["metadata"]
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_create_notification_contact_supports_internal_audit_source(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = "leaseflow.internal"

    try:
        created = db.create_notification_contact(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            email=f"internal-contact-{uuid4().hex[:8]}@example.com",
            audit_source="leaseflow.internal",
        )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            audit_rows = conn.execute(
                """
                SELECT actor_user_id, metadata
                FROM audit_logs
                WHERE tenant_id = %s
                  AND entity_id = %s
                  AND action = 'notification_contact.create'
                """,
                (tenant_id, created.contact_id),
            ).fetchall()

        assert len(audit_rows) == 1
        assert audit_rows[0]["actor_user_id"] == actor_user_id
        assert audit_rows[0]["metadata"] == {
            "source": "leaseflow.internal",
            "enabled": True,
        }
        assert "email" not in audit_rows[0]["metadata"]
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_create_notification_contact_rejects_blank_email(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"

    try:
        with pytest.raises(ValueError, match="Notification contact email must not be empty."):
            db.create_notification_contact(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                email="   ",
            )
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_list_notification_contacts_returns_requested_tenant_and_filters_enabled(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    other_tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"

    try:
        enabled = db.create_notification_contact(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            email=f"enabled-{uuid4().hex[:8]}@example.com",
        )
        disabled = db.create_notification_contact(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            email=f"disabled-{uuid4().hex[:8]}@example.com",
            enabled=False,
        )
        db.create_notification_contact(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            email=enabled.email,
        )

        all_contacts = db.list_notification_contacts(tenant_id=tenant_id)
        enabled_contacts = db.list_notification_contacts(tenant_id=tenant_id, enabled_only=True)

        assert {item.contact_id for item in all_contacts} == {
            enabled.contact_id,
            disabled.contact_id,
        }
        assert {item.email for item in all_contacts} == {enabled.email, disabled.email}
        assert [item.contact_id for item in enabled_contacts] == [enabled.contact_id]
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)
        _cleanup_test_tenant(integration_settings, other_tenant_id)


def test_create_notification_contact_rejects_duplicate_email_case_insensitive_per_tenant(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    other_tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"

    try:
        created = db.create_notification_contact(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            email="Recipient.Dupe@Example.COM",
        )

        with pytest.raises(
            ValueError,
            match="Notification contact already exists for tenant.",
        ):
            db.create_notification_contact(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                email=" recipient.dupe@example.com ",
            )

        other_created = db.create_notification_contact(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            email="recipient.dupe@example.com",
        )

        assert created.email == "recipient.dupe@example.com"
        assert other_created.email == "recipient.dupe@example.com"
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)
        _cleanup_test_tenant(integration_settings, other_tenant_id)


def test_set_notification_contact_enabled_updates_tenant_contact_and_audit_log(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"

    try:
        created = db.create_notification_contact(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            email=f"toggle-{uuid4().hex[:8]}@example.com",
        )

        updated = db.set_notification_contact_enabled(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            contact_id=created.contact_id,
            enabled=False,
        )
        enabled_contacts = db.list_notification_contacts(tenant_id=tenant_id, enabled_only=True)

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            audit_rows = conn.execute(
                """
                SELECT tenant_id, actor_user_id, action, entity_type, entity_id, metadata
                FROM audit_logs
                WHERE tenant_id = %s
                  AND entity_id = %s
                  AND action = 'notification_contact.update'
                """,
                (tenant_id, created.contact_id),
            ).fetchall()

        assert updated.contact_id == created.contact_id
        assert updated.enabled is False
        assert enabled_contacts == []

        assert len(audit_rows) == 1
        assert audit_rows[0]["tenant_id"] == tenant_id
        assert audit_rows[0]["actor_user_id"] == actor_user_id
        assert audit_rows[0]["entity_type"] == "notification_contact"
        assert audit_rows[0]["entity_id"] == created.contact_id
        assert audit_rows[0]["metadata"] == {"source": "api", "enabled": False}
        assert "email" not in audit_rows[0]["metadata"]
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_set_notification_contact_enabled_rejects_cross_tenant_access(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    other_tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"

    try:
        other_contact = db.create_notification_contact(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            email=f"cross-tenant-{uuid4().hex[:8]}@example.com",
        )

        with pytest.raises(LookupError, match="Notification contact not found for tenant."):
            db.set_notification_contact_enabled(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                contact_id=other_contact.contact_id,
                enabled=False,
            )

        other_contacts = db.list_notification_contacts(tenant_id=other_tenant_id)

        assert len(other_contacts) == 1
        assert other_contacts[0].contact_id == other_contact.contact_id
        assert other_contacts[0].enabled is True
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
            (row["tenant_id"], row["lease_id"], row["type"], row["due_date"]) for row in rows
        } == {
            (tenant_id, lease_record.lease_id, "rent_due_soon", date(2026, 4, 5)),
            (other_tenant_id, other_lease.lease_id, "rent_due_soon", date(2026, 4, 6)),
        }
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)
        _cleanup_test_tenant(integration_settings, other_tenant_id)


def test_notification_email_delivery_rows_are_idempotent_and_retry_safe(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"

    try:
        property_record = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=f"Delivery HQ {uuid4().hex[:8]}",
            address=f"Delivery Street {uuid4().hex[:8]}",
        )
        db.create_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name=f"Delivery User {uuid4().hex[:8]}",
            rent_due_day_of_month=5,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        contact = db.create_notification_contact(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            email=f"delivery-{uuid4().hex[:8]}@example.com",
        )
        db.create_due_lease_reminder_notifications(
            tenant_id=tenant_id,
            as_of_date=date(2026, 4, 3),
            days=7,
        )

        first_prepare = db.create_missing_notification_email_deliveries(tenant_id=tenant_id)
        second_prepare = db.create_missing_notification_email_deliveries(tenant_id=tenant_id)
        pending = db.list_pending_notification_email_deliveries(
            tenant_id=tenant_id,
            max_attempts=3,
            limit=10,
        )

        assert first_prepare.tenant_id == tenant_id
        assert first_prepare.candidate_count == 1
        assert first_prepare.created_count == 1
        assert first_prepare.duplicate_count == 0
        assert second_prepare.candidate_count == 1
        assert second_prepare.created_count == 0
        assert second_prepare.duplicate_count == 1
        assert len(pending) == 1
        assert pending[0].tenant_id == tenant_id
        assert pending[0].contact_id == contact.contact_id
        assert pending[0].recipient_email == contact.email
        assert pending[0].subject == "Rent due soon"
        assert pending[0].body == "Rent is due in 2 days."

        db.mark_notification_email_delivery_sent(
            tenant_id=tenant_id,
            delivery_id=pending[0].delivery_id,
        )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            audit_rows = conn.execute(
                """
                SELECT action, metadata
                FROM audit_logs
                WHERE tenant_id = %s
                  AND entity_id = %s
                  AND action = 'notification_email_delivery.sent'
                """,
                (tenant_id, pending[0].delivery_id),
            ).fetchall()

        assert (
            db.list_pending_notification_email_deliveries(
                tenant_id=tenant_id,
                max_attempts=3,
                limit=10,
            )
            == []
        )
        assert len(audit_rows) == 1
        assert audit_rows[0]["metadata"] == {"source": "internal", "status": "sent"}
        assert "email" not in audit_rows[0]["metadata"]
        assert "message" not in audit_rows[0]["metadata"]
        assert "body" not in audit_rows[0]["metadata"]
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_notification_email_delivery_excludes_disabled_contacts_and_stops_after_max_attempts(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"

    try:
        property_record = db.create_property(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            name=f"Delivery Retry HQ {uuid4().hex[:8]}",
            address=f"Delivery Retry Street {uuid4().hex[:8]}",
        )
        db.create_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name=f"Delivery Retry User {uuid4().hex[:8]}",
            rent_due_day_of_month=5,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        enabled_contact = db.create_notification_contact(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            email=f"enabled-{uuid4().hex[:8]}@example.com",
        )
        db.create_notification_contact(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            email=f"disabled-{uuid4().hex[:8]}@example.com",
            enabled=False,
        )
        db.create_due_lease_reminder_notifications(
            tenant_id=tenant_id,
            as_of_date=date(2026, 4, 3),
            days=7,
        )
        db.create_missing_notification_email_deliveries(tenant_id=tenant_id)
        pending = db.list_pending_notification_email_deliveries(
            tenant_id=tenant_id,
            max_attempts=2,
            limit=10,
        )

        assert len(pending) == 1
        assert pending[0].contact_id == enabled_contact.contact_id

        db.mark_notification_email_delivery_failed(
            tenant_id=tenant_id,
            delivery_id=pending[0].delivery_id,
            error_code="smtp_transient_error",
        )
        retry_pending = db.list_pending_notification_email_deliveries(
            tenant_id=tenant_id,
            max_attempts=2,
            limit=10,
        )
        assert [item.delivery_id for item in retry_pending] == [pending[0].delivery_id]

        db.mark_notification_email_delivery_failed(
            tenant_id=tenant_id,
            delivery_id=pending[0].delivery_id,
            error_code="smtp_transient_error",
        )

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            audit_rows = conn.execute(
                """
                SELECT metadata
                FROM audit_logs
                WHERE tenant_id = %s
                  AND entity_id = %s
                  AND action = 'notification_email_delivery.failed'
                ORDER BY created_at ASC
                """,
                (tenant_id, pending[0].delivery_id),
            ).fetchall()

        assert (
            db.list_pending_notification_email_deliveries(
                tenant_id=tenant_id,
                max_attempts=2,
                limit=10,
            )
            == []
        )
        assert [row["metadata"] for row in audit_rows] == [
            {
                "source": "internal",
                "status": "failed",
                "error_code": "smtp_transient_error",
            },
            {
                "source": "internal",
                "status": "failed",
                "error_code": "smtp_transient_error",
            },
        ]
        for row in audit_rows:
            assert "email" not in row["metadata"]
            assert "message" not in row["metadata"]
            assert "body" not in row["metadata"]
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)


def test_notification_email_delivery_rejects_cross_tenant_status_update(
    integration_settings: Settings,
) -> None:
    db = Database(integration_settings)
    tenant_id = f"test-local-{uuid4().hex}"
    other_tenant_id = f"test-local-{uuid4().hex}"
    actor_user_id = f"user-{uuid4().hex[:12]}"

    try:
        property_record = db.create_property(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            name=f"Cross Delivery HQ {uuid4().hex[:8]}",
            address=f"Cross Delivery Street {uuid4().hex[:8]}",
        )
        db.create_lease(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name=f"Cross Delivery User {uuid4().hex[:8]}",
            rent_due_day_of_month=5,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        db.create_notification_contact(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            email=f"cross-{uuid4().hex[:8]}@example.com",
        )
        db.create_due_lease_reminder_notifications(
            tenant_id=other_tenant_id,
            as_of_date=date(2026, 4, 3),
            days=7,
        )
        db.create_missing_notification_email_deliveries(tenant_id=other_tenant_id)
        other_delivery = db.list_pending_notification_email_deliveries(
            tenant_id=other_tenant_id,
            max_attempts=3,
            limit=10,
        )[0]

        with pytest.raises(LookupError, match="Notification email delivery not found for tenant."):
            db.mark_notification_email_delivery_sent(
                tenant_id=tenant_id,
                delivery_id=other_delivery.delivery_id,
            )

        with pytest.raises(LookupError, match="Notification email delivery not found for tenant."):
            db.mark_notification_email_delivery_failed(
                tenant_id=tenant_id,
                delivery_id=other_delivery.delivery_id,
                error_code="smtp_transient_error",
            )
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)
        _cleanup_test_tenant(integration_settings, other_tenant_id)


def test_list_notifications_includes_tenant_scoped_email_delivery_summary(
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
            name=f"Delivery Summary HQ {uuid4().hex[:8]}",
            address=f"Delivery Summary Street {uuid4().hex[:8]}",
        )
        other_property = db.create_property(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            name=f"Other Delivery Summary HQ {uuid4().hex[:8]}",
            address=f"Other Delivery Summary Street {uuid4().hex[:8]}",
        )
        db.create_lease(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            property_id=property_record.property_id,
            resident_name=f"Delivery Summary User {uuid4().hex[:8]}",
            rent_due_day_of_month=5,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        db.create_lease(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            property_id=other_property.property_id,
            resident_name=f"Other Delivery Summary User {uuid4().hex[:8]}",
            rent_due_day_of_month=5,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        contact_one = db.create_notification_contact(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            email=f"summary-one-{uuid4().hex[:8]}@example.com",
        )
        contact_two = db.create_notification_contact(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            email=f"summary-two-{uuid4().hex[:8]}@example.com",
        )
        db.create_notification_contact(
            tenant_id=other_tenant_id,
            actor_user_id=actor_user_id,
            email=f"summary-other-{uuid4().hex[:8]}@example.com",
        )
        db.create_due_lease_reminder_notifications(
            tenant_id=tenant_id,
            as_of_date=date(2026, 4, 3),
            days=7,
        )
        db.create_due_lease_reminder_notifications(
            tenant_id=other_tenant_id,
            as_of_date=date(2026, 4, 3),
            days=7,
        )
        db.create_missing_notification_email_deliveries(tenant_id=tenant_id)
        db.create_missing_notification_email_deliveries(tenant_id=other_tenant_id)

        notifications = db.list_notifications(tenant_id=tenant_id)
        summary = notifications[0].delivery_summary

        with psycopg.connect(integration_settings.db_dsn(), row_factory=dict_row) as conn:
            conn.execute(
                """
                UPDATE notification_email_deliveries
                SET status = 'sent',
                    attempt_count = 1,
                    last_attempt_at = '2026-05-04T10:00:00+00:00'::timestamptz,
                    sent_at = '2026-05-04T10:00:00+00:00'::timestamptz,
                    updated_at = '2026-05-04T10:00:00+00:00'::timestamptz
                WHERE tenant_id = %s AND contact_id = %s
                """,
                (tenant_id, contact_one.contact_id),
            )
            conn.execute(
                """
                UPDATE notification_email_deliveries
                SET status = 'failed',
                    attempt_count = 1,
                    last_attempt_at = '2026-05-04T11:00:00+00:00'::timestamptz,
                    last_error_code = 'smtp_network_error',
                    updated_at = '2026-05-04T11:00:00+00:00'::timestamptz
                WHERE tenant_id = %s AND contact_id = %s
                """,
                (tenant_id, contact_two.contact_id),
            )

        notifications = db.list_notifications(tenant_id=tenant_id)
        summary = notifications[0].delivery_summary

        assert len(notifications) == 1
        assert summary.total_count == 2
        assert summary.pending_count == 0
        assert summary.sent_count == 1
        assert summary.failed_count == 1
        assert summary.latest_attempt_at is not None
        assert summary.latest_attempt_at.isoformat() == "2026-05-04T11:00:00+00:00"
        assert summary.latest_sent_at is not None
        assert summary.latest_sent_at.isoformat() == "2026-05-04T10:00:00+00:00"
        assert summary.last_error_code == "smtp_network_error"

        serialized = notification_to_dict(notifications[0])
        assert "tenant_id" not in serialized
        assert "contact_id" not in str(serialized)
        assert "recipient_email" not in str(serialized)
        assert contact_one.email not in str(summary)
        assert contact_two.email not in str(summary)
    finally:
        _cleanup_test_tenant(integration_settings, tenant_id)
        _cleanup_test_tenant(integration_settings, other_tenant_id)
