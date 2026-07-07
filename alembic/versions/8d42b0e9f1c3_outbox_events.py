"""outbox events

Revision ID: 8d42b0e9f1c3
Revises: d4f6a7b8c9e0
Create Date: 2026-07-04 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "8d42b0e9f1c3"
down_revision = "d4f6a7b8c9e0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "outbox_event",
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=True),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("entity", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "topic",
            "event_id",
            name="uq_outbox_event_topic_event_id",
        ),
    )
    op.create_index("ix_outbox_event_entity", "outbox_event", ["entity"])
    op.create_index("ix_outbox_event_entity_id", "outbox_event", ["entity_id"])
    op.create_index("ix_outbox_event_event_type", "outbox_event", ["event_type"])
    op.create_index("ix_outbox_event_next_attempt_at", "outbox_event", ["next_attempt_at"])
    op.create_index(
        "ix_outbox_event_pending_next_attempt_id",
        "outbox_event",
        ["next_attempt_at", "id"],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index("ix_outbox_event_published_at", "outbox_event", ["published_at"])
    op.create_index("ix_outbox_event_status", "outbox_event", ["status"])
    op.create_index("ix_outbox_event_topic", "outbox_event", ["topic"])


def downgrade():
    op.drop_index("ix_outbox_event_topic", table_name="outbox_event")
    op.drop_index("ix_outbox_event_status", table_name="outbox_event")
    op.drop_index("ix_outbox_event_published_at", table_name="outbox_event")
    op.drop_index("ix_outbox_event_pending_next_attempt_id", table_name="outbox_event")
    op.drop_index("ix_outbox_event_next_attempt_at", table_name="outbox_event")
    op.drop_index("ix_outbox_event_event_type", table_name="outbox_event")
    op.drop_index("ix_outbox_event_entity_id", table_name="outbox_event")
    op.drop_index("ix_outbox_event_entity", table_name="outbox_event")
    op.drop_table("outbox_event")
