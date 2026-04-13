from auto_parking.db.models.base import Base as Base
from auto_parking.db.models.base import BaseORM as BaseORM
from auto_parking.db.models.driver import Driver as Driver
from auto_parking.db.models.enterprise import Enterprise as Enterprise
from auto_parking.db.models.enterprise import user_enterprise as user_enterprise
from auto_parking.db.models.user import User as User
from auto_parking.db.models.vehicle import Vehicle as Vehicle
from auto_parking.db.models.vehicle_gps_point import VehicleGpsPoint as VehicleGpsPoint
from auto_parking.db.models.vehicle_model import VehicleModel as VehicleModel
from auto_parking.db.models.vehicle_to_driver import (
    VehicleDriverAssignment as VehicleDriverAssignment,
)

ADMIN_MODELS = (
    Driver,
    Enterprise,
    Vehicle,
    VehicleModel,
    VehicleDriverAssignment,
)
