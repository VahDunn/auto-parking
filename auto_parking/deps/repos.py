from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.deps.commons import depends_db
from auto_parking.repo.driver import DriverRepository
from auto_parking.repo.enterprise import EnterpriseRepository
from auto_parking.repo.vehicle import VehicleRepository


def get_enterprise_repo(
    db: AsyncSession = depends_db,
) -> EnterpriseRepository:
    return EnterpriseRepository(db)


def get_vehicle_repo(
    db: AsyncSession = depends_db,
) -> VehicleRepository:
    return VehicleRepository(db)


def get_driver_repo(
    db: AsyncSession = depends_db,
) -> DriverRepository:
    return DriverRepository(db)


dep_enterprise_repo = Depends(get_enterprise_repo)
dep_vehicle_repo = Depends(get_vehicle_repo)
dep_driver_repo = Depends(get_driver_repo)
