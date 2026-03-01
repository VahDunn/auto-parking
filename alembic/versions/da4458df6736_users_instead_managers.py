"""users_istead_managers

Revision ID: da4458df6736
Revises: 691fd6282453
Create Date: 2026-03-02 12:38:16.462668
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "da4458df6736"
down_revision = "691fd6282453"
branch_labels = None
depends_on = None


def upgrade():
    # 1) Create enum type if not exists (Postgres)
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE user_role AS ENUM ('admin', 'manager', 'user');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    # 2) Create user table
    op.create_table(
        "user",
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("admin", "manager", "user", name="user_role", create_type=False),
            server_default="user",
            nullable=False,
        ),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_role"), "user", ["role"], unique=False)
    op.create_index(op.f("ix_user_username"), "user", ["username"], unique=True)

    # 3) Create user_enterprise table
    op.create_table(
        "user_enterprise",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("enterprise_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["enterprise_id"], ["enterprise.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "enterprise_id"),
        sa.UniqueConstraint("user_id", "enterprise_id", name="uq_user_enterprise"),
    )

    # 4) Data migration: manager -> user (keep ids)
    op.execute(
        sa.text(
            """
            INSERT INTO "user" (id, username, password_hash, role, created_at)
            SELECT id, username, password_hash, 'manager', created_at
            FROM manager
            """
        )
    )

    # 5) Data migration: manager_enterprise -> user_enterprise
    op.execute(
        sa.text(
            """
            INSERT INTO user_enterprise (user_id, enterprise_id)
            SELECT manager_id, enterprise_id
            FROM manager_enterprise
            """
        )
    )

    # 6) Drop old tables (order matters)
    op.drop_table("manager_enterprise")
    op.drop_table("manager")


def downgrade():
    # 1) Recreate manager + manager_enterprise
    op.create_table(
        "manager",
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name=op.f("uq_manager_username")),
    )
    op.create_index(op.f("ix_manager_username"), "manager", ["username"], unique=True)

    op.create_table(
        "manager_enterprise",
        sa.Column("manager_id", sa.BigInteger(), nullable=False),
        sa.Column("enterprise_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["enterprise_id"], ["enterprise.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manager_id"], ["manager.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("manager_id", "enterprise_id"),
        sa.UniqueConstraint("manager_id", "enterprise_id", name="uq_manager_enterprise"),
    )

    # 2) Data back-migration: user(role=manager) -> manager (keep ids)
    op.execute(
        sa.text(
            """
            INSERT INTO manager (id, username, password_hash, created_at)
            SELECT id, username, password_hash, created_at
            FROM "user"
            WHERE role = 'manager'
            """
        )
    )

    # 3) Data back-migration: user_enterprise -> manager_enterprise (only for role=manager)
    op.execute(
        sa.text(
            """
            INSERT INTO manager_enterprise (manager_id, enterprise_id)
            SELECT ue.user_id, ue.enterprise_id
            FROM user_enterprise ue
            JOIN "user" u ON u.id = ue.user_id
            WHERE u.role = 'manager'
            """
        )
    )

    # 4) Drop new tables
    op.drop_table("user_enterprise")
    op.drop_index(op.f("ix_user_username"), table_name="user")
    op.drop_index(op.f("ix_user_role"), table_name="user")
    op.drop_table("user")

    # 5) Drop enum type
    op.execute("DROP TYPE IF EXISTS user_role CASCADE;")
