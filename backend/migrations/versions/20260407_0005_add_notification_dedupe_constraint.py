"""Add notification dedupe constraint for due reminder scans."""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260407_0005"
down_revision = "20260407_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_notifications_tenant_lease_type_due_date",
        "notifications",
        ["tenant_id", "lease_id", "type", "due_date"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_notifications_tenant_lease_type_due_date",
        "notifications",
        type_="unique",
    )
