"""experimental_branch

Revision ID: 9be5b0b54024
Revises: cdbec0af3d5a
Create Date: 2026-03-04 11:47:59.434012

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "9be5b0b54024"
down_revision = "cdbec0af3d5a"
branch_labels = ("experimental",)
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vehicle",
        sa.Column("deep_nest_val", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vehicle", "deep_nest_val")
