"""Add tenant-scoped notification contacts."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260430_0007"
down_revision = "20260409_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_contacts",
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "length(btrim(email)) > 0",
            name="ck_notification_contacts_email_not_blank",
        ),
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_notification_contacts_tenant_email_lower
        ON notification_contacts (tenant_id, lower(email))
        """
    )
    op.create_index(
        "ix_notification_contacts_tenant_enabled",
        "notification_contacts",
        ["tenant_id", "enabled"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notification_contacts_tenant_enabled", table_name="notification_contacts")
    op.drop_index(
        "uq_notification_contacts_tenant_email_lower",
        table_name="notification_contacts",
    )
    op.drop_table("notification_contacts")
