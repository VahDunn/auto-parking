from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto_parking.core.domain import ReportPeriod, ReportType
from auto_parking.db.models.base import BaseORM

if TYPE_CHECKING:
    from auto_parking.db.models import Enterprise, Vehicle


class Report(BaseORM):
    __tablename__: str = "report"

    name: Mapped[str] = mapped_column(sa.String, nullable=False)

    report_type: Mapped[ReportType] = mapped_column(
        sa.Enum(ReportType, name="report_type"),
        nullable=False,
        index=True,
    )

    period: Mapped[ReportPeriod] = mapped_column(
        sa.Enum(ReportPeriod, name="report_period"),
        nullable=False,
    )

    date_from: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    date_to: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)

    enterprise_id: Mapped[int] = mapped_column(
        sa.ForeignKey("enterprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    vehicle_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("vehicle.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    params_json: Mapped[dict[str, Any]] = mapped_column(
        sa.JSON,
        nullable=False,
        default=dict,
    )

    result_json: Mapped[list[dict[str, Any]]] = mapped_column(
        sa.JSON,
        nullable=False,
        default=list,
    )

    enterprise: Mapped["Enterprise"] = relationship("Enterprise", lazy="selectin")
    vehicle: Mapped["Vehicle | None"] = relationship("Vehicle", lazy="selectin")
