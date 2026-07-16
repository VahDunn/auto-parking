from auto_parking.app.api.v1.enterprises.crud import router as crud_router
from auto_parking.app.api.v1.enterprises.exports import router as exports_router
from auto_parking.app.api.v1.enterprises.imports import router as imports_router

router = crud_router

router.include_router(exports_router)
router.include_router(imports_router)
