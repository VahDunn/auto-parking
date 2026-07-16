from fastapi import Depends

from auto_parking.app.deps.cache import get_cache_client
from auto_parking.app.deps.integrations import get_reverse_geocoder
from auto_parking.app.deps.notifications import notification_publisher
from auto_parking.app.deps.repos import (
    dep_driver_repo,
    dep_enterprise_repo,
    dep_manager_repo,
    dep_notification_repo,
    dep_outbox_repo,
    dep_report_repo,
    dep_track_repo,
    dep_trip_repo,
    dep_vehicle_model_repo,
    dep_vehicle_repo,
)
from auto_parking.app.service.driver import DriverService
from auto_parking.app.service.enterprise import EnterpriseService
from auto_parking.app.service.export import ExportService
from auto_parking.app.service.gpx_import import GpxImportService
from auto_parking.app.service.import_ import ImportService
from auto_parking.app.service.notification import NotificationService
from auto_parking.app.service.report import ReportService
from auto_parking.app.service.report_pdf import ReportPdfBuilder
from auto_parking.app.service.trip import TripService
from auto_parking.app.service.trip_track import TripTrackService
from auto_parking.app.service.user import UserService
from auto_parking.app.service.vehicle import VehicleService
from auto_parking.app.service.vehicle_model import VehicleModelService
from auto_parking.app.service.vehicle_track import VehicleTrackService
from auto_parking.core.config import settings
from auto_parking.infrastructure.db.repositories.driver import DriverRepository
from auto_parking.infrastructure.db.repositories.enterprise import EnterpriseRepository
from auto_parking.infrastructure.db.repositories.notification import NotificationRepository
from auto_parking.infrastructure.db.repositories.outbox import OutboxRepository
from auto_parking.infrastructure.db.repositories.report import ReportRepository
from auto_parking.infrastructure.db.repositories.trip import TripRepository
from auto_parking.infrastructure.db.repositories.user import UserRepository
from auto_parking.infrastructure.db.repositories.vehicle import VehicleRepository
from auto_parking.infrastructure.db.repositories.vehicle_model import VehicleModelRepository
from auto_parking.infrastructure.db.repositories.vehicle_track import VehicleTrackRepository


def get_enterprise_service(
    repo: EnterpriseRepository = dep_enterprise_repo,
) -> EnterpriseService:
    return EnterpriseService(repo)


def get_driver_service(repo: DriverRepository = dep_driver_repo) -> DriverService:
    return DriverService(repo)


def get_vehicle_service(
    repo: VehicleRepository = dep_vehicle_repo,
    outbox_repo: OutboxRepository = dep_outbox_repo,
) -> VehicleService:
    return VehicleService(
        repo,
        cache=get_cache_client(),
        cache_ttl_seconds=settings.entity_cache_ttl_seconds,
        outbox_repo=outbox_repo,
    )


def get_vehicle_model_service(
    repo: VehicleModelRepository = dep_vehicle_model_repo,
) -> VehicleModelService:
    return VehicleModelService(
        repo,
        cache=get_cache_client(),
        cache_ttl_seconds=settings.vehicle_model_cache_ttl_seconds,
    )


def get_user_service(repo: UserRepository = dep_manager_repo) -> UserService:
    return UserService(repo)


def get_vehicle_track_service(
    track_repo: VehicleTrackRepository = dep_track_repo,
) -> VehicleTrackService:
    return VehicleTrackService(
        track_repo=track_repo,
        cache=get_cache_client(),
        cache_ttl_seconds=settings.vehicle_track_cache_ttl_seconds,
    )


def get_notification_service(
    notification_repo: NotificationRepository = dep_notification_repo,
    user_repo: UserRepository = dep_manager_repo,
) -> NotificationService:
    return NotificationService(
        notification_repo=notification_repo,
        user_repo=user_repo,
        publisher=notification_publisher,
    )


def get_trip_service(
    repo: TripRepository = dep_trip_repo,
    notification_service: NotificationService = Depends(get_notification_service),
) -> TripService:
    return TripService(
        repo,
        geocoder=get_reverse_geocoder(),
        notification_service=notification_service,
    )


def get_trip_track_service(
    trip_repo: TripRepository = dep_trip_repo,
    track_repo: VehicleTrackRepository = dep_track_repo,
    vehicle_repo: VehicleRepository = dep_vehicle_repo,
):
    return TripTrackService(vehicle_repo=vehicle_repo, track_repo=track_repo, trip_repo=trip_repo)


def get_export_service(
    enterprise_repo: EnterpriseRepository = dep_enterprise_repo,
    vehicle_repo: VehicleRepository = dep_vehicle_repo,
    trip_repo: TripRepository = dep_trip_repo,
    track_repo: VehicleTrackRepository = dep_track_repo,
    driver_repo: DriverRepository = dep_driver_repo,
) -> ExportService:
    return ExportService(
        enterprise_repo=enterprise_repo,
        vehicle_repo=vehicle_repo,
        trip_repo=trip_repo,
        track_repo=track_repo,
        driver_repo=driver_repo,
    )


def get_import_service(
    enterprise_repo: EnterpriseRepository = dep_enterprise_repo,
    vehicle_repo: VehicleRepository = dep_vehicle_repo,
    track_repo: VehicleTrackRepository = dep_track_repo,
    trip_service: TripService = Depends(get_trip_service),
) -> ImportService:
    return ImportService(
        enterprise_repo=enterprise_repo,
        vehicle_repo=vehicle_repo,
        track_repo=track_repo,
        trip_service=trip_service,
    )


def get_report_service(
    report_repo: ReportRepository = dep_report_repo,
    trip_repo: TripRepository = dep_trip_repo,
    vehicle_repo: VehicleRepository = dep_vehicle_repo,
) -> ReportService:
    return ReportService(
        report_repo=report_repo,
        trip_repo=trip_repo,
        vehicle_repo=vehicle_repo,
    )


def get_gpx_import_service(
    vehicle_repo: VehicleRepository = dep_vehicle_repo,
    trip_repo: TripRepository = dep_trip_repo,
    track_repo: VehicleTrackRepository = dep_track_repo,
    trip_service: TripService = Depends(get_trip_service),
) -> GpxImportService:
    return GpxImportService(
        vehicle_repo=vehicle_repo,
        trip_repo=trip_repo,
        track_repo=track_repo,
        trip_service=trip_service,
    )


def get_reports_pdf_service():
    return ReportPdfBuilder()


dep_import_service = Depends(get_import_service)
dep_trip_service = Depends(get_trip_service)
dep_vehicle_track_service = Depends(get_vehicle_track_service)
dep_enterprise_service = Depends(get_enterprise_service)
dep_driver_service = Depends(get_driver_service)
dep_vehicle_service = Depends(get_vehicle_service)
dep_vehicle_model_service = Depends(get_vehicle_model_service)
dep_user_service = Depends(get_user_service)
dep_trip_track_service = Depends(get_trip_track_service)
dep_export_service = Depends(get_export_service)
dep_report_service = Depends(get_report_service)
dep_reports_pdf_service = Depends(get_reports_pdf_service)
dep_gpx_import_service = Depends(get_gpx_import_service)
dep_notification_service = Depends(get_notification_service)
