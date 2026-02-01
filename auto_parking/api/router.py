from fastapi import APIRouter

from auto_parking.api.v1.vehicle_models import router as vehicle_models_router
from auto_parking.api.v1.vehicles import router as vehicles_router

api_router = APIRouter()
api_router.include_router(vehicles_router, prefix="/vehicles", tags=["vehicles"])
api_router.include_router(vehicle_models_router, prefix="/vehicle-models", tags=["vehicle-models"])


@api_router.get("/health")
async def health_check():
    return {"status": "ok"}
