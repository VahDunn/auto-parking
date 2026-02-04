from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from auto_parking.core.errors import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)


async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(
        status_code=400,
        content={"message": str(exc)},
    )


async def not_found_handler(_: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={"message": str(exc)},
    )


async def forbidden_handler(_: Request, exc: ForbiddenError):
    return JSONResponse(
        status_code=403,
        content={"message": str(exc)},
    )


async def conflict_handler(_: Request, exc: ConflictError):
    return JSONResponse(
        status_code=409,
        content={"message": str(exc)},
    )


EXCEPTION_HANDLERS: list[tuple[type[Exception], Callable]] = [
    (AppError, app_error_handler),
    (NotFoundError, not_found_handler),
    (ForbiddenError, forbidden_handler),
    (ConflictError, conflict_handler),
]


def register_exception_handlers(app: FastAPI) -> None:
    for exc_type, handler in EXCEPTION_HANDLERS:
        app.add_exception_handler(exc_type, handler)
