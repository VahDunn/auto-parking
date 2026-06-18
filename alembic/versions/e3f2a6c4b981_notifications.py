"""notifications

Revision ID: e3f2a6c4b981
Revises: 5c78afb41084
Create Date: 2026-05-28 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "e3f2a6c4b981"
down_revision = "5c78afb41084"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification",
        sa.Column("recipient_user_id", sa.BigInteger(), nullable=False),
        sa.Column("enterprise_id", sa.BigInteger(), nullable=False),
        sa.Column("trip_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["enterprise_id"],
            ["enterprise.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["user.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["trip_id"],
            ["trip.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "recipient_user_id",
            "type",
            "trip_id",
            name="uq_notification_recipient_type_trip",
        ),
    )
    op.create_index("ix_notification_enterprise_id", "notification", ["enterprise_id"])
    op.create_index("ix_notification_read_at", "notification", ["read_at"])
    op.create_index(
        "ix_notification_recipient_read_created",
        "notification",
        ["recipient_user_id", "read_at", "created_at"],
    )
    op.create_index("ix_notification_recipient_user_id", "notification", ["recipient_user_id"])
    op.create_index("ix_notification_trip_id", "notification", ["trip_id"])
    op.create_index("ix_notification_type", "notification", ["type"])


def downgrade():
    op.drop_index("ix_notification_type", table_name="notification")
    op.drop_index("ix_notification_trip_id", table_name="notification")
    op.drop_index("ix_notification_recipient_user_id", table_name="notification")
    op.drop_index("ix_notification_recipient_read_created", table_name="notification")
    op.drop_index("ix_notification_read_at", table_name="notification")
    op.drop_index("ix_notification_enterprise_id", table_name="notification")
    op.drop_table("notification")
