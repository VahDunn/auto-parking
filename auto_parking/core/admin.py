from fastapi import FastAPI
from sqladmin import Admin, ModelView

from auto_parking.db.engine import engine
from auto_parking.db.models import Vehicle, VehicleModel


class VehicleAdmin(ModelView, model=Vehicle):
    column_list = [
        Vehicle.id,
        Vehicle.vehicle_number,
        Vehicle.model,
        Vehicle.accident_number,
        Vehicle.price,
        Vehicle.created_at,
    ]
    column_searchable_list = [
        Vehicle.vehicle_number,
        Vehicle.id,
    ]
    form_excluded_columns = ["created_at"]
    name = "Vehicle"
    name_plural = "Vehicles"
    icon = "fa-solid fa-car"


class VehicleModelAdmin(ModelView, model=VehicleModel):
    column_list = [
        VehicleModel.id,
        VehicleModel.name,
        VehicleModel.type,
        VehicleModel.horse_powers,
        VehicleModel.seats_number,
        VehicleModel.fuel_capacity_liters,
        VehicleModel.created_at,
    ]
    column_searchable_list = [
        VehicleModel.name,
        VehicleModel.type,
        VehicleModel.id,
    ]
    form_excluded_columns = ["created_at"]
    name = "Vehicle Model"
    name_plural = "Vehicle Models"
    icon = "fa-solid fa-list"


def setup_admin(app: FastAPI) -> Admin:
    admin = Admin(app, engine)
    admin.add_view(VehicleAdmin)
    admin.add_view(VehicleModelAdmin)
    return admin
