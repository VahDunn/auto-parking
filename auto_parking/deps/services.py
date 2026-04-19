from fastapi import Depends

from auto_parking.deps.repos import (
    dep_driver_repo,
    dep_enterprise_repo,
    dep_manager_repo,
    dep_track_repo,
    dep_trip_repo,
    dep_vehicle_repo,
)
from auto_parking.repo.driver import DriverRepository
from auto_parking.repo.enterprise import EnterpriseRepository
from auto_parking.repo.trip import TripRepository
from auto_parking.repo.user import UserRepository
from auto_parking.repo.vehicle import VehicleRepository
from auto_parking.repo.vehicle_track import VehicleTrackRepository
from auto_parking.service.driver import DriverService
from auto_parking.service.enterprise import EnterpriseService
from auto_parking.service.trip import TripService
from auto_parking.service.trip_track import TripTrackService
from auto_parking.service.user import UserService
from auto_parking.service.vehicle import VehicleService
from auto_parking.service.vehicle_track import VehicleTrackService


def get_enterprise_service(
    repo: EnterpriseRepository = dep_enterprise_repo,
) -> EnterpriseService:
    return EnterpriseService(repo)


def get_driver_service(repo: DriverRepository = dep_driver_repo) -> DriverService:
    return DriverService(repo)


def get_vehicle_service(repo: VehicleRepository = dep_vehicle_repo) -> VehicleService:
    return VehicleService(repo)


def get_user_service(repo: UserRepository = dep_manager_repo) -> UserService:
    return UserService(repo)


def get_vehicle_track_service(
    vehicle_repo: VehicleRepository = dep_vehicle_repo,
    track_repo: VehicleTrackRepository = dep_track_repo,
) -> VehicleTrackService:
    return VehicleTrackService(vehicle_repo=vehicle_repo, track_repo=track_repo)


def get_trip_service(repo: TripRepository = dep_trip_repo) -> TripService:
    return TripService(repo)


def get_trip_track_service(
    trip_repo: TripRepository = dep_trip_repo,
    track_repo: VehicleTrackRepository = dep_track_repo,
    vehicle_repo: VehicleRepository = dep_vehicle_repo,
):
    return TripTrackService(vehicle_repo=vehicle_repo, track_repo=track_repo, trip_repo=trip_repo)


dep_trip_service = Depends(get_trip_service)
dep_vehicle_track_service = Depends(get_vehicle_track_service)
dep_enterprise_service = Depends(get_enterprise_service)
dep_driver_service = Depends(get_driver_service)
dep_vehicle_service = Depends(get_vehicle_service)
dep_user_service = Depends(get_user_service)
dep_trip_track_service = Depends(get_trip_track_service)
