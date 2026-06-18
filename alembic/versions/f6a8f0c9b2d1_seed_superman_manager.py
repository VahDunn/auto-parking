"""seed superman manager

Revision ID: f6a8f0c9b2d1
Revises: e3f2a6c4b981
Create Date: 2026-05-29 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "f6a8f0c9b2d1"
down_revision = "e3f2a6c4b981"
branch_labels = None
depends_on = None


SUPERMAN_PASSWORD_HASH = "$2b$12$UiPAu7oiyKPU.7a5dwyVWuksXQbHI76zH8nFOR3KQMg93RWtE5vV2"


def upgrade():
    op.execute(
        sa.text(
            """
            WITH upserted_user AS (
                INSERT INTO "user" (username, password_hash, role)
                VALUES ('superman', :password_hash, 'manager')
                ON CONFLICT (username)
                DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    role = 'manager'
                RETURNING id
            ),
            target_user AS (
                SELECT id FROM upserted_user
                UNION
                SELECT id FROM "user" WHERE username = 'superman'
            ),
            target_enterprise AS (
                SELECT id FROM enterprise WHERE name = 'Handsome Family' LIMIT 1
            )
            INSERT INTO user_enterprise (user_id, enterprise_id)
            SELECT target_user.id, target_enterprise.id
            FROM target_user, target_enterprise
            ON CONFLICT (user_id, enterprise_id) DO NOTHING
            """
        ).bindparams(password_hash=SUPERMAN_PASSWORD_HASH)
    )
    op.execute(
        sa.text(
            """
            DELETE FROM notification
            WHERE recipient_user_id IN (
                SELECT id FROM "user" WHERE role = 'admin'
            )
            """
        )
    )


def downgrade():
    op.execute(
        sa.text(
            """
            DELETE FROM notification
            WHERE recipient_user_id = (
                SELECT id FROM "user" WHERE username = 'superman'
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM user_enterprise
            WHERE user_id = (
                SELECT id FROM "user" WHERE username = 'superman'
            )
            """
        )
    )
    op.execute(sa.text("""DELETE FROM "user" WHERE username = 'superman'"""))
