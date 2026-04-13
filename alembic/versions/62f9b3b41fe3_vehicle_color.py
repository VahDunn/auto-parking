"""vehicle_color

Revision ID: 62f9b3b41fe3
Revises: da4458df6736
Create Date: 2026-03-12 09:22:35.606502
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "62f9b3b41fe3"
down_revision = "da4458df6736"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "vehicle",
        sa.Column(
            "color",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text(
                """
                (ARRAY[
                'Black','Blue','Green','Red','Yellow',
                'Белый','Синий','Зелёный','Красный','Жёлтый'
                ])[floor(random()*10 + 1)]
                """
            ),
        ),
    )


def downgrade():
    op.drop_column("vehicle", "color")
