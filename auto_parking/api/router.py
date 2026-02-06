from fastapi import APIRouter

from auto_parking.api.v1.drivers import router as drivers_router
from auto_parking.api.v1.enterprises import router as enterprises_router
from auto_parking.api.v1.vehicle_models import router as vehicle_models_router
from auto_parking.api.v1.vehicles import router as vehicles_router
from auto_parking.deps.commons import dep_verify_user

api_router = APIRouter(dependencies=[dep_verify_user])
api_router.include_router(vehicles_router, prefix="/vehicles", tags=["vehicles"])
api_router.include_router(vehicle_models_router, prefix="/vehicle-models", tags=["vehicle-models"])
api_router.include_router(drivers_router, prefix="/drivers", tags=["drivers"])
api_router.include_router(
    enterprises_router,
    prefix="/enterprises",
    tags=["enterprises"],
)


@api_router.get("/health")
async def health_check():
    return {"status": "ok"}
