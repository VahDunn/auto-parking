from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app_main: FastAPI):
    # startup
    yield
    # shutdown
    # await engine.dispose()


def create_app() -> FastAPI:
    main_app = FastAPI(
        title="Receptor API",
        version="1.0.0",
        lifespan=lifespan,
    )
    # register_exception_handlers(main_app)
    # main_app.include_router(api_router, prefix='/api/v1')

    return main_app


app = create_app()
