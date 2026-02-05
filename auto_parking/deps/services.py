from fastapi import Depends

from auto_parking.deps.repos import (
    depends_driver_repo,
    depends_enterprise_repo,
    depends_vehicle_repo,
)
from auto_parking.repo.driver import DriverRepository
from auto_parking.repo.enterprise import EnterpriseRepository
from auto_parking.repo.vehicle import VehicleRepository
from auto_parking.service.driver import DriverService
from auto_parking.service.enterprise import EnterpriseService
from auto_parking.service.vehicle import VehicleService


def get_enterprise_service(
    repo: EnterpriseRepository = depends_enterprise_repo,
) -> EnterpriseService:
    return EnterpriseService(repo)


def get_driver_service(repo: DriverRepository = depends_driver_repo) -> DriverService:
    return DriverService(repo)


def get_vehicle_service(repo: VehicleRepository = depends_vehicle_repo) -> VehicleService:
    return VehicleService(repo)


depends_enterprise_service = Depends(get_enterprise_service)
depends_driver_service = Depends(get_driver_service)
depends_vehicle_service = Depends(get_vehicle_service)
