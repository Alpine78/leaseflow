"""Add notifications table for tenant-scoped reminder records."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260407_0004"
down_revision = "20260407_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_leases_tenant_lease",
        "leases",
        ["tenant_id", "lease_id"],
    )

    op.create_table(
        "notifications",
        sa.Column(
            "notification_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("lease_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "lease_id"],
            ["leases.tenant_id", "leases.lease_id"],
            name="fk_notifications_lease_tenant",
        ),
    )
    op.create_index(
        "ix_notifications_tenant_created_at",
        "notifications",
        ["tenant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_tenant_type_due_date",
        "notifications",
        ["tenant_id", "type", "due_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_tenant_type_due_date", table_name="notifications")
    op.drop_index("ix_notifications_tenant_created_at", table_name="notifications")
    op.drop_table("notifications")
    op.drop_constraint("uq_leases_tenant_lease", "leases", type_="unique")
