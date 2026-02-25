import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from auto_parking.api.router import api_router
from auto_parking.core.handlers import register_exception_handlers
from auto_parking.core.security.admin_basic import AdminBasicAuthMiddleware
from auto_parking.db.admin import setup_admin
from auto_parking.db.engine import engine
from auto_parking.db.events import register_listeners


@asynccontextmanager
async def lifespan(app_main: FastAPI):
    register_listeners()
    # startup
    yield
    # shutdown
    await engine.dispose()


def setup_logger(log_level="INFO"):
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_logger.addHandler(console_handler)

    if log_level.upper() == "DEBUG":
        sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
        sqlalchemy_logger.setLevel(logging.INFO)
        sqlalchemy_logger.addHandler(console_handler)


def create_app() -> FastAPI:
    main_app = FastAPI(
        title="Receptor API",
        version="1.0.0",
        lifespan=lifespan,
    )
    register_exception_handlers(main_app)
    setup_admin(main_app)
    # register_exception_handlers(main_app)
    main_app.include_router(api_router, prefix="/api")
    main_app.add_middleware(AdminBasicAuthMiddleware)
    return main_app


app = create_app()
