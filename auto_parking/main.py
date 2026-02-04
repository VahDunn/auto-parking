from contextlib import asynccontextmanager

from fastapi import FastAPI

from auto_parking.api.router import api_router
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


def create_app() -> FastAPI:
    main_app = FastAPI(
        title="Receptor API",
        version="1.0.0",
        lifespan=lifespan,
    )
    setup_admin(main_app)
    # register_exception_handlers(main_app)
    main_app.include_router(api_router, prefix="/api")
    return main_app


app = create_app()
