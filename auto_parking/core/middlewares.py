from fastapi import Request
from fastapi.responses import JSONResponse

from auto_parking.core.errors import AppError


async def app_error_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except AppError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "error": exc.__class__.__name__,
                "message": str(exc),
            },
        )
