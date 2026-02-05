from fastapi import Depends

from auto_parking.deps.repos import (
    dep_driver_repo,
    dep_enterprise_repo,
    dep_vehicle_repo,
)
from auto_parking.repo.driver import DriverRepository
from auto_parking.repo.enterprise import EnterpriseRepository
from auto_parking.repo.vehicle import VehicleRepository
from auto_parking.service.driver import DriverService
from auto_parking.service.enterprise import EnterpriseService
from auto_parking.service.vehicle import VehicleService


def get_enterprise_service(
    repo: EnterpriseRepository = dep_enterprise_repo,
) -> EnterpriseService:
    return EnterpriseService(repo)


def get_driver_service(repo: DriverRepository = dep_driver_repo) -> DriverService:
    return DriverService(repo)


def get_vehicle_service(repo: VehicleRepository = dep_vehicle_repo) -> VehicleService:
    return VehicleService(repo)


dep_enterprise_service = Depends(get_enterprise_service)
dep_driver_service = Depends(get_driver_service)
dep_vehicle_service = Depends(get_vehicle_service)
