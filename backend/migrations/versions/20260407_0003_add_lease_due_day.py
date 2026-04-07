"""Add reminder-ready rent due day to leases."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260407_0003"
down_revision = "20260407_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leases",
        sa.Column("rent_due_day_of_month", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_leases_rent_due_day_of_month",
        "leases",
        "rent_due_day_of_month IS NULL OR rent_due_day_of_month BETWEEN 1 AND 31",
    )


def downgrade() -> None:
    op.drop_constraint("ck_leases_rent_due_day_of_month", "leases", type_="check")
    op.drop_column("leases", "rent_due_day_of_month")
