# pyright: ignore
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI
from sqladmin import Admin, ModelView
from wtforms.fields.simple import PasswordField
from wtforms.validators import DataRequired, Length

from auto_parking.core.security.passwords import hash_password
from auto_parking.db.engine import engine
from auto_parking.db.models import (
    Driver,
    Enterprise,
    User,
    Vehicle,
    VehicleDriverAssignment,
    VehicleModel,
)


class VehicleAdmin(ModelView, model=Vehicle):
    column_list = [
        Vehicle.id,
        Vehicle.vehicle_number,
        Vehicle.model,
        Vehicle.enterprise,
        Vehicle.color,
        Vehicle.purchased_at_utc,
    ]
    column_details_list = column_list
    column_searchable_list = [
        Vehicle.vehicle_number,
        Vehicle.id,
        Vehicle.color,
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
        Enterprise.timezone,
        Enterprise.created_at,
    ]
    column_searchable_list = [
        Enterprise.name,
        Enterprise.settlement,
        Enterprise.id,
        Enterprise.timezone,
    ]
    form_columns = [
        Enterprise.name,
        Enterprise.settlement,
        Enterprise.timezone,
    ]
    name = "Enterprise"
    name_plural = "Enterprises"
    icon = "fa-solid fa-building"

    async def on_model_change(self, data, model, is_created, request):
        tz = data.get("timezone")

        if tz == "":
            model.timezone = None
        elif tz:
            try:
                ZoneInfo(tz)
            except ZoneInfoNotFoundError:
                raise ValueError("Invalid timezone") from None

        return await super().on_model_change(data, model, is_created, request)


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


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username]
    column_searchable_list = [User.username, User.id]
    column_details_list = [User.id, User.username, User.enterprises]
    form_excluded_columns = ["created_at", "password_hash"]

    async def scaffold_form(self, rules=None):
        Form = await super().scaffold_form(rules)
        Form.password = PasswordField(
            "Password",
            validators=[
                DataRequired(message="Password is required"),
                Length(min=6, message="Min 6 characters"),
            ],
        )
        return Form

    async def on_model_change(self, data, model, is_created, request):
        raw_password = data.get("password")
        if is_created and not raw_password:
            raise ValueError("Password is required")

        if raw_password:
            model.password_hash = hash_password(raw_password)

        data.pop("password", None)
        return await super().on_model_change(data, model, is_created, request)


def setup_admin(app: FastAPI) -> Admin:
    admin = Admin(app, engine)

    admin.add_view(VehicleAdmin)
    admin.add_view(VehicleModelAdmin)
    admin.add_view(EnterpriseAdmin)
    admin.add_view(DriverAdmin)
    admin.add_view(VehicleDriverAssignmentAdmin)
    admin.add_view(UserAdmin)

    return admin
