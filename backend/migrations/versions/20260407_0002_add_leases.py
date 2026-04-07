"""Add leases table with tenant-safe property reference."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260407_0002"
down_revision = "20260310_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_properties_tenant_property",
        "properties",
        ["tenant_id", "property_id"],
    )

    op.create_table(
        "leases",
        sa.Column(
            "lease_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resident_name", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "property_id"],
            ["properties.tenant_id", "properties.property_id"],
            name="fk_leases_property_tenant",
        ),
    )
    op.create_index(
        "ix_leases_tenant_created_at",
        "leases",
        ["tenant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_leases_tenant_property",
        "leases",
        ["tenant_id", "property_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_leases_tenant_property", table_name="leases")
    op.drop_index("ix_leases_tenant_created_at", table_name="leases")
    op.drop_table("leases")
    op.drop_constraint("uq_properties_tenant_property", "properties", type_="unique")
