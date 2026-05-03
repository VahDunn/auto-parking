"""reports

Revision ID: 5c78afb41084
Revises: 3694fe164b30
Create Date: 2026-05-03 11:11:16.581785
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "5c78afb41084"
down_revision = "3694fe164b30"
branch_labels = None
depends_on = None


report_type_enum = postgresql.ENUM(
    "vehicle_mileage",
    "vehicle_activity",
    "vehicle_geography",
    name="report_type",
    create_type=False,
)

report_period_enum = postgresql.ENUM(
    "day",
    "month",
    "year",
    name="report_period",
    create_type=False,
)


def upgrade():
    report_type_enum.create(op.get_bind(), checkfirst=True)
    report_period_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "report",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("report_type", report_type_enum, nullable=False),
        sa.Column("period", report_period_enum, nullable=False),
        sa.Column("date_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("date_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("enterprise_id", sa.BigInteger(), nullable=False),
        sa.Column("vehicle_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "params_json",
            sa.JSON(),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column(
            "result_json",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["enterprise_id"], ["enterprise.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicle.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_report_enterprise_id", "report", ["enterprise_id"])
    op.create_index("ix_report_report_type", "report", ["report_type"])
    op.create_index("ix_report_vehicle_id", "report", ["vehicle_id"])


def downgrade():
    op.drop_index("ix_report_vehicle_id", table_name="report")
    op.drop_index("ix_report_report_type", table_name="report")
    op.drop_index("ix_report_enterprise_id", table_name="report")
    op.drop_table("report")

    report_period_enum.drop(op.get_bind(), checkfirst=True)
    report_type_enum.drop(op.get_bind(), checkfirst=True)