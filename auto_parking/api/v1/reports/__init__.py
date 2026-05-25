from auto_parking.api.v1.reports.crud import router
from auto_parking.api.v1.reports.exports import router as exports_router

router.include_router(exports_router)
