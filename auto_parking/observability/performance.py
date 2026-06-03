import json
import logging
from datetime import UTC, datetime

logger = logging.getLogger("auto_parking.performance")


def log_http_request(
    *,
    method: str,
    path: str,
    status: int,
    duration_seconds: float,
) -> None:
    _log_event(
        "http_request",
        method=method,
        path=path,
        status=status,
        duration_ms=_milliseconds(duration_seconds),
    )


def log_cache_lookup(
    *,
    operation: str,
    result: str,
    duration_seconds: float,
) -> None:
    _log_event(
        "cache_lookup",
        operation=operation,
        result=result,
        duration_ms=_milliseconds(duration_seconds),
    )


def _log_event(event: str, **fields: object) -> None:
    logger.info(
        json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "event": event,
                **fields,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )


def _milliseconds(duration_seconds: float) -> float:
    return round(duration_seconds * 1000, 3)
