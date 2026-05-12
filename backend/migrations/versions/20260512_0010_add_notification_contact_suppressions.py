"""Add tenant-scoped notification contact suppressions."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260512_0010"
down_revision = "20260508_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_contact_suppressions",
        sa.Column(
            "suppression_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "reason IN ('bounce', 'complaint')",
            name="ck_notification_contact_suppressions_reason",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "contact_id"],
            ["notification_contacts.tenant_id", "notification_contacts.contact_id"],
            name="fk_notification_contact_suppressions_contact_tenant",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "contact_id",
            "reason",
            name="uq_notification_contact_suppressions_tenant_contact_reason",
        ),
    )
    op.create_index(
        "ix_notification_contact_suppressions_tenant_contact",
        "notification_contact_suppressions",
        ["tenant_id", "contact_id"],
        unique=False,
    )
    op.create_index(
        "ix_notification_contact_suppressions_tenant_reason",
        "notification_contact_suppressions",
        ["tenant_id", "reason"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_contact_suppressions_tenant_reason",
        table_name="notification_contact_suppressions",
    )
    op.drop_index(
        "ix_notification_contact_suppressions_tenant_contact",
        table_name="notification_contact_suppressions",
    )
    op.drop_table("notification_contact_suppressions")
