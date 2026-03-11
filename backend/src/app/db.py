from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.config import Settings
from app.models import Property


class Database:
    def __init__(self, settings: Settings) -> None:
        self._dsn = settings.db_dsn()

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
