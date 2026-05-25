from fastapi import APIRouter, HTTPException

from auto_parking.api.schemas.vehicle_model import VehicleModelOut
from auto_parking.core.domain.models import VehicleModelInfo
from auto_parking.deps.services import dep_vehicle_model_service
from auto_parking.service.vehicle_model import VehicleModelService

router = APIRouter()


def _vehicle_model_out(model: VehicleModelInfo) -> VehicleModelOut:
    return VehicleModelOut(**model.to_dict())


@router.get("", response_model=list[VehicleModelOut])
async def get_vehicle_models(service: VehicleModelService = dep_vehicle_model_service):
    return [_vehicle_model_out(model) for model in await service.get_all()]


@router.get("/{id}", response_model=VehicleModelOut)
async def get_vehicle_model(id: int, service: VehicleModelService = dep_vehicle_model_service):
    model = await service.get_by_id(id)
    if model is None:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    return _vehicle_model_out(model)
