from time import perf_counter

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from auto_parking.observability.performance import log_http_request

REQUESTS_TOTAL = Counter(
    "auto_parking_http_requests_total",
    "Total HTTP requests.",
    ("method", "path", "status"),
)
REQUEST_DURATION_SECONDS = Histogram(
    "auto_parking_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "path"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


def setup_metrics(app: FastAPI) -> None:
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        started_at = perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            path = _route_path(request)
            duration_seconds = perf_counter() - started_at
            REQUESTS_TOTAL.labels(
                method=request.method,
                path=path,
                status=str(status_code),
            ).inc()
            REQUEST_DURATION_SECONDS.labels(
                method=request.method,
                path=path,
            ).observe(duration_seconds)
            log_http_request(
                method=request.method,
                path=path,
                status=status_code,
                duration_seconds=duration_seconds,
            )

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _route_path(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str):
        return path
    return request.url.path
