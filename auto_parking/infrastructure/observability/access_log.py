import logging
from urllib.parse import parse_qsl, urlencode

from fastapi import Request

logger = logging.getLogger("auto_parking.access")

SENSITIVE_QUERY_KEYS = {"access_token", "auth", "jwt", "password", "token"}


def log_access_request(
    *,
    request: Request,
    status: int,
    bytes_sent: int,
    duration_seconds: float,
) -> None:
    timestamp = int(request.scope.get("time") or 0)
    if timestamp <= 0:
        timestamp = int(_timestamp_from_duration(duration_seconds))

    logger.info(
        '%s - - [%s] "%s" %s %s "%s" "%s" %s',
        _client_host(request),
        timestamp,
        _request_line(request),
        status,
        max(bytes_sent, 0),
        _header_or_dash(request, "referer"),
        _header_or_dash(request, "user-agent"),
        round(duration_seconds * 1000, 3),
    )


def _client_host(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip() or "-"

    if request.client is None:
        return "-"

    return request.client.host


def _request_line(request: Request) -> str:
    path = request.url.path
    query = _redacted_query(request.url.query)
    target = f"{path}?{query}" if query else path
    http_version = request.scope.get("http_version") or "1.1"
    return f"{request.method} {target} HTTP/{http_version}"


def _redacted_query(query: str) -> str:
    if not query:
        return ""

    pairs = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        if key.lower() in SENSITIVE_QUERY_KEYS:
            pairs.append((key, "REDACTED"))
        else:
            pairs.append((key, value))
    return urlencode(pairs)


def _header_or_dash(request: Request, name: str) -> str:
    value = request.headers.get(name)
    return value if value else "-"


def _timestamp_from_duration(duration_seconds: float) -> float:
    # Fallback used only if middleware did not set request.scope["time"].
    from time import time

    return time() - duration_seconds
