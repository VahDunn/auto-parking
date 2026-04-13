from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.deps.commons import depends_db
from auto_parking.repo.driver import DriverRepository
from auto_parking.repo.enterprise import EnterpriseRepository
from auto_parking.repo.user import UserRepository
from auto_parking.repo.vehicle import VehicleRepository
from auto_parking.repo.vehicle_track import VehicleTrackRepository


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


def get_manager_repo(
    db: AsyncSession = depends_db,
) -> UserRepository:
    return UserRepository(db)


def get_vehicle_track_repo(
    db: AsyncSession = depends_db,
) -> VehicleTrackRepository:
    return VehicleTrackRepository(db)


dep_enterprise_repo = Depends(get_enterprise_repo)
dep_vehicle_repo = Depends(get_vehicle_repo)
dep_driver_repo = Depends(get_driver_repo)
dep_manager_repo = Depends(get_manager_repo)
dep_track_repo = Depends(get_vehicle_track_repo)
