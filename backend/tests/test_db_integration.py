from __future__ import annotations

import os
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row
from psycopg.sql import Identifier, Literal, SQL

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
            conn.execute("DELETE FROM audit_logs WHERE tenant_id = %s", (tenant_id,))
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
