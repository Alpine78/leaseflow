"""Add tenant-scoped notification email deliveries."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260504_0008"
down_revision = "20260430_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_notifications_tenant_notification",
        "notifications",
        ["tenant_id", "notification_id"],
    )
    op.create_unique_constraint(
        "uq_notification_contacts_tenant_contact",
        "notification_contacts",
        ["tenant_id", "contact_id"],
    )

    op.create_table(
        "notification_email_deliveries",
        sa.Column(
            "delivery_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'failed')",
            name="ck_notification_email_deliveries_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_notification_email_deliveries_attempt_count_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "notification_id"],
            ["notifications.tenant_id", "notifications.notification_id"],
            name="fk_notification_email_deliveries_notification_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "contact_id"],
            ["notification_contacts.tenant_id", "notification_contacts.contact_id"],
            name="fk_notification_email_deliveries_contact_tenant",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "notification_id",
            "contact_id",
            name="uq_notification_email_deliveries_tenant_notification_contact",
        ),
    )
    op.create_index(
        "ix_notification_email_deliveries_tenant_status_attempts",
        "notification_email_deliveries",
        ["tenant_id", "status", "attempt_count"],
        unique=False,
    )
    op.create_index(
        "ix_notification_email_deliveries_tenant_notification",
        "notification_email_deliveries",
        ["tenant_id", "notification_id"],
        unique=False,
    )
    op.create_index(
        "ix_notification_email_deliveries_tenant_contact",
        "notification_email_deliveries",
        ["tenant_id", "contact_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_email_deliveries_tenant_contact",
        table_name="notification_email_deliveries",
    )
    op.drop_index(
        "ix_notification_email_deliveries_tenant_notification",
        table_name="notification_email_deliveries",
    )
    op.drop_index(
        "ix_notification_email_deliveries_tenant_status_attempts",
        table_name="notification_email_deliveries",
    )
    op.drop_table("notification_email_deliveries")
    op.drop_constraint(
        "uq_notification_contacts_tenant_contact",
        "notification_contacts",
        type_="unique",
    )
    op.drop_constraint(
        "uq_notifications_tenant_notification",
        "notifications",
        type_="unique",
    )
