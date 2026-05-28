from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from auto_parking.core.domain.enums import ReportPeriod, ReportType
from auto_parking.core.domain.models.base import DomainModel


@dataclass(slots=True)
class ReportModel(DomainModel):
    id: int | None
    name: str
    report_type: ReportType
    period: ReportPeriod
    date_from: datetime
    date_to: datetime
    enterprise_id: int
    vehicle_id: int | None
    params_json: dict[str, Any]
    result_json: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime | None = None


@dataclass(slots=True)
class ReportInfoModel(DomainModel):
    type: ReportType
    title: str
    description: str
    parameters: list[str] = field(default_factory=list)
