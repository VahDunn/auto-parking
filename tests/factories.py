from datetime import datetime, timezone

from auto_parking.core.domain.enums import ReportPeriod, ReportType
from auto_parking.core.domain.models import (
    EnterpriseModel,
    ReportModel,
    TripModel,
    TripPointModel,
    VehicleModel,
)


def vehicle_model(vehicle_id: int = 1, enterprise_id: int = 10) -> VehicleModel:
    return VehicleModel(
        id=vehicle_id,
        price=1000,
        mileage=500,
        vehicle_number="А123ВС77",
        owners_count=1,
        accident_number=0,
        manufacture_year=2020,
        model_id=2,
        color="black",
        enterprise_id=enterprise_id,
        drivers=[11],
        active_driver_id=11,
        purchased_at_utc=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
        purchased_at_enterprise=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        enterprise_timezone="UTC",
    )


def enterprise_model(enterprise_id: int = 10) -> EnterpriseModel:
    return EnterpriseModel(
        id=enterprise_id,
        name="Enterprise",
        settlement="Moscow",
        vehicles=[1],
        drivers=[11],
        managers=[5],
        timezone="Europe/Moscow",
    )


def trip_model(trip_id: int = 7, vehicle_id: int = 1) -> TripModel:
    start = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    end = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    point = TripPointModel(
        id=101,
        recorded_at_utc=start,
        recorded_at_enterprise=start,
        latitude=55.75,
        longitude=37.61,
    )
    return TripModel(
        id=trip_id,
        vehicle_id=vehicle_id,
        started_at_utc=start,
        ended_at_utc=end,
        started_at_enterprise=start,
        ended_at_enterprise=end,
        start_point=point,
        end_point=point,
        enterprise_timezone="UTC",
    )


def report_model(report_id: int = 3, enterprise_id: int = 10) -> ReportModel:
    return ReportModel(
        id=report_id,
        name="Mileage",
        report_type=ReportType.vehicle_mileage,
        period=ReportPeriod.day,
        date_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
        date_to=datetime(2026, 1, 2, tzinfo=timezone.utc),
        enterprise_id=enterprise_id,
        vehicle_id=1,
        params_json={},
        result_json=[{"time": "2026-01-01", "value": 12.5, "extra": {"unit": "km"}}],
        created_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
    )
