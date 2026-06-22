"""hot endpoint indexes

Revision ID: d4f6a7b8c9e0
Revises: b9d2e8f6c1a4
Create Date: 2026-06-18 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "d4f6a7b8c9e0"
down_revision = "b9d2e8f6c1a4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_driver_enterprise_id",
        "driver",
        ["enterprise_id"],
    )
    op.create_index(
        "ix_user_enterprise_enterprise_user",
        "user_enterprise",
        ["enterprise_id", "user_id"],
    )
    op.create_index(
        "ix_notification_recipient_created_id",
        "notification",
        ["recipient_user_id", "created_at", "id"],
    )
    op.create_index(
        "ix_notification_unread_recipient_created_id",
        "notification",
        ["recipient_user_id", "created_at", "id"],
        postgresql_where=sa.text("read_at IS NULL"),
    )


def downgrade():
    op.drop_index(
        "ix_notification_unread_recipient_created_id",
        table_name="notification",
    )
    op.drop_index("ix_notification_recipient_created_id", table_name="notification")
    op.drop_index("ix_user_enterprise_enterprise_user", table_name="user_enterprise")
    op.drop_index("ix_driver_enterprise_id", table_name="driver")
