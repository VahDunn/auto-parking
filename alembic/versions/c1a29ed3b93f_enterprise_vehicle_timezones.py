"""enterprise vehicle timezones

Revision ID: c1a29ed3b93f
Revises: 62f9b3b41fe3
Create Date: 2026-04-08

"""

import sqlalchemy as sa

from alembic import op  # pyright: ignore[reportAttributeAccessIssue]

revision = "c1a29ed3b93f"
down_revision = "62f9b3b41fe3"
branch_labels = None
depends_on = None


def upgrade():
    # 👉 добавляем timezone предприятию
    op.add_column("enterprise", sa.Column("timezone", sa.String(), nullable=True))

    # 👉 добавляем время покупки машине
    op.add_column(
        "vehicle", sa.Column("purchased_at_utc", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade():
    op.drop_column("vehicle", "purchased_at_utc")
    op.drop_column("enterprise", "timezone")
