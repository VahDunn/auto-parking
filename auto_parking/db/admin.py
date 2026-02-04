from fastapi import FastAPI
from sqladmin import Admin, ModelView

from auto_parking.db.engine import engine
from auto_parking.db.models import (
    Driver,
    Enterprise,
    Vehicle,
    VehicleDriverAssignment,
    VehicleModel,
)


class VehicleAdmin(ModelView, model=Vehicle):
    column_list = [
        Vehicle.id,
        Vehicle.vehicle_number,
        Vehicle.model,
        Vehicle.accident_number,
        Vehicle.price,
        Vehicle.created_at,
        Vehicle.enterprise_id,
    ]
    column_details_list = column_list
    column_searchable_list = [
        Vehicle.vehicle_number,
        Vehicle.id,
    ]
    form_excluded_columns = ["created_at", "drivers"]
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


class EnterpriseAdmin(ModelView, model=Enterprise):
    column_list = [
        Enterprise.id,
        Enterprise.name,
        Enterprise.settlement,
        Enterprise.created_at,
    ]
    column_searchable_list = [
        Enterprise.name,
        Enterprise.settlement,
        Enterprise.id,
    ]
    form_excluded_columns = ["created_at"]
    name = "Enterprise"
    name_plural = "Enterprises"
    icon = "fa-solid fa-building"


class DriverAdmin(ModelView, model=Driver):
    column_list = [
        Driver.id,
        Driver.name,
        Driver.salary_rub,
        Driver.enterprise,
        Driver.active_vehicle,
        Driver.created_at,
        Driver.enterprise_id,
    ]
    column_details_list = column_list
    column_searchable_list = [
        Driver.name,
        Driver.id,
    ]
    form_excluded_columns = ["created_at", "vehicles"]
    name = "Driver"
    name_plural = "Drivers"
    icon = "fa-solid fa-id-card"


class VehicleDriverAssignmentAdmin(ModelView, model=VehicleDriverAssignment):
    column_list = [
        VehicleDriverAssignment.vehicle,
        VehicleDriverAssignment.driver,
    ]
    column_searchable_list = [
        VehicleDriverAssignment.vehicle_id,
        VehicleDriverAssignment.driver_id,
    ]
    form_columns = ["vehicle", "driver"]
    name = "Vehicle–Driver Assignment"
    name_plural = "Vehicle–Driver Assignments"
    icon = "fa-solid fa-link"


def setup_admin(app: FastAPI) -> Admin:
    admin = Admin(app, engine)

    admin.add_view(VehicleAdmin)
    admin.add_view(VehicleModelAdmin)

    admin.add_view(EnterpriseAdmin)
    admin.add_view(DriverAdmin)
    admin.add_view(VehicleDriverAssignmentAdmin)

    return admin


# Отладочная админка для всех моделей подряд со всеми колонками подряд
# from fastapi import FastAPI
# from sqladmin import Admin, ModelView
# from sqlalchemy import inspect
#
# from auto_parking.db.engine import engine
# from auto_parking.db.models import ADMIN_MODELS
#
#
# def setup_admin(app: FastAPI) -> Admin:
#     admin = Admin(app, engine)
#
#     for model_cls in ADMIN_MODELS:
#         mapper = inspect(model_cls)
#
#         cols = [c.key for c in mapper.columns]
#
#         view_cls = type(
#             f"{model_cls.__name__}Admin",
#             (ModelView,),
#             {
#                 "name": model_cls.__name__,
#                 "name_plural": f"{model_cls.__name__}s",
#                 "column_list": cols,
#                 "form_columns": cols,
#             },
#             model=model_cls,
#         )
#
#         admin.add_view(view_cls)
#
#     return admin
