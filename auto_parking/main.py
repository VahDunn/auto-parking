from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from auto_parking.api.router import api_router
from auto_parking.core.handlers import register_exception_handlers
from auto_parking.core.logger import setup_logging
from auto_parking.db.admin import setup_admin
from auto_parking.db.engine import engine
from auto_parking.db.events import register_listeners
from auto_parking.deps.events import close_event_producer
from auto_parking.integrations.monitoring import setup_metrics
from auto_parking.realtime.gps import gps_realtime_hub


@asynccontextmanager
async def lifespan(app_main: FastAPI):
    register_listeners()
    await gps_realtime_hub.start()
    yield
    await gps_realtime_hub.stop()
    await close_event_producer()
    await engine.dispose()


def create_app() -> FastAPI:
    main_app = FastAPI(
        title="Auto- API",
        version="1.0.0",
        lifespan=lifespan,
    )
    main_app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8080",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    setup_metrics(main_app)
    register_exception_handlers(main_app)
    setup_admin(main_app)
    main_app.include_router(api_router, prefix="/api")
    return main_app


setup_logging()
app = create_app()
