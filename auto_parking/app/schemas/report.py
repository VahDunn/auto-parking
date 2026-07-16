from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from auto_parking.app.schemas.base import ApiSchema
from auto_parking.core.domain.enums.report_period import ReportPeriod
from auto_parking.core.domain.enums.report_type import ReportType
from auto_parking.core.domain.models import ReportModel


class ReportInfo(ApiSchema):
    type: ReportType
    title: str
    description: str
    parameters: list[str]


class ReportPoint(ApiSchema):
    time: str
    value: float | int
    extra: dict[str, Any] = Field(default_factory=dict)


class ReportCreate(ApiSchema):
    name: str
    report_type: ReportType
    period: ReportPeriod
    date_from: datetime
    date_to: datetime
    enterprise_id: int
    vehicle_id: int | None = None
    params_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("date_from", "date_to")
    @classmethod
    def validate_aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime must be timezone-aware")
        return value

    def to_domain_model(self) -> ReportModel:
        return ReportModel(
            id=None,
            name=self.name,
            report_type=self.report_type,
            period=self.period,
            date_from=self.date_from,
            date_to=self.date_to,
            enterprise_id=self.enterprise_id,
            vehicle_id=self.vehicle_id,
            params_json=self.params_json,
        )


class ReportOut(ApiSchema):
    id: int
    name: str
    report_type: ReportType
    period: ReportPeriod
    date_from: datetime
    date_to: datetime
    enterprise_id: int
    vehicle_id: int | None = None
    params_json: dict[str, Any]
    result_json: list[dict[str, Any]]
    created_at: datetime
