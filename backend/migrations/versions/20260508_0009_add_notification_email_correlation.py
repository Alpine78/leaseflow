"""Add notification email event correlation token."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260508_0009"
down_revision = "20260504_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notification_email_deliveries",
        sa.Column("event_correlation_token", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        """
        UPDATE notification_email_deliveries
        SET event_correlation_token = gen_random_uuid()
        WHERE event_correlation_token IS NULL
        """
    )
    op.alter_column(
        "notification_email_deliveries",
        "event_correlation_token",
        nullable=False,
        server_default=sa.text("gen_random_uuid()"),
        existing_type=postgresql.UUID(as_uuid=True),
    )
    op.create_index(
        "uq_notification_email_deliveries_event_correlation_token",
        "notification_email_deliveries",
        ["event_correlation_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_notification_email_deliveries_event_correlation_token",
        table_name="notification_email_deliveries",
    )
    op.drop_column("notification_email_deliveries", "event_correlation_token")
