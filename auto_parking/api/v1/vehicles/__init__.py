from auto_parking.api.v1.vehicles.crud import router as crud_router
from auto_parking.api.v1.vehicles.exports import router as exports_router
from auto_parking.api.v1.vehicles.tracks import router as tracks_router
from auto_parking.api.v1.vehicles.trips import router as trips_router

router = crud_router

router.include_router(exports_router)
router.include_router(trips_router)
router.include_router(tracks_router)
