from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from auto_parking.app.api.router import api_router
from auto_parking.app.deps.events import close_event_producer, get_event_producer
from auto_parking.app.service.outbox import OutboxDispatcher
from auto_parking.core.config import settings
from auto_parking.core.handlers import register_exception_handlers
from auto_parking.core.logger import setup_logging
from auto_parking.infrastructure.db.admin import setup_admin
from auto_parking.infrastructure.db.engine import AsyncSessionLocal, engine
from auto_parking.infrastructure.db.events import register_listeners
from auto_parking.infrastructure.observability import (
    setup_database_metrics,
    setup_metrics,
    setup_tracing,
    shutdown_tracing,
)
from auto_parking.infrastructure.realtime.gps import gps_realtime_hub

outbox_dispatcher = OutboxDispatcher(
    sessionmaker=AsyncSessionLocal,
    producer_factory=get_event_producer,
    batch_size=settings.outbox_dispatcher_batch_size,
    poll_interval_seconds=settings.outbox_dispatcher_poll_interval_seconds,
    retry_delay_seconds=settings.outbox_dispatcher_retry_delay_seconds,
    max_attempts=settings.outbox_dispatcher_max_attempts,
)


@asynccontextmanager
async def lifespan(app_main: FastAPI):
    register_listeners()
    if settings.outbox_dispatcher_enabled and settings.kafka_bootstrap_servers:
        await outbox_dispatcher.start()
    if settings.gps_consumer_enabled:
        await gps_realtime_hub.start()
    yield
    if settings.gps_consumer_enabled:
        await gps_realtime_hub.stop()
    if settings.outbox_dispatcher_enabled and settings.kafka_bootstrap_servers:
        await outbox_dispatcher.stop()
    await close_event_producer()
    await engine.dispose()
    shutdown_tracing(app_main)


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
    setup_database_metrics(engine)
    setup_tracing(main_app, engine)
    register_exception_handlers(main_app)
    setup_admin(main_app)
    main_app.include_router(api_router, prefix="/api")
    return main_app


setup_logging()
app = create_app()
