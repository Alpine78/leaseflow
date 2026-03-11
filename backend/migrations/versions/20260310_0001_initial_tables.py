"""Initial properties and audit log tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260310_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    op.create_table(
        "properties",
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_properties_tenant_id",
        "properties",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_properties_tenant_created_at",
        "properties",
        ["tenant_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "audit_logs",
        sa.Column(
            "audit_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_audit_logs_tenant_created_at",
        "audit_logs",
        ["tenant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_tenant_entity",
        "audit_logs",
        ["tenant_id", "entity_type", "entity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_tenant_entity", table_name="audit_logs")
    op.drop_index("ix_audit_logs_tenant_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_properties_tenant_created_at", table_name="properties")
    op.drop_index("ix_properties_tenant_id", table_name="properties")
    op.drop_table("properties")
