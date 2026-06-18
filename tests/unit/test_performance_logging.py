import json
from types import SimpleNamespace
from unittest.mock import patch

from starlette.datastructures import URL, Headers

from auto_parking.core.logger import get_logging_config
from auto_parking.observability.access_log import log_access_request
from auto_parking.observability.performance import log_cache_lookup, log_http_request


def test_logging_config_keeps_httpx_credentials_out_of_info_logs():
    config = get_logging_config()

    assert config["loggers"]["httpx"]["level"] == "WARNING"
    assert config["handlers"]["performance"]["class"] == "logging.handlers.RotatingFileHandler"
    assert config["handlers"]["app_access"]["class"] == "logging.handlers.RotatingFileHandler"


def test_http_request_log_is_structured_json():
    with patch("auto_parking.observability.performance.logger.info") as info:
        log_http_request(
            method="GET",
            path="/api/vehicles/{id}/track",
            status=200,
            duration_seconds=0.012345,
        )

    payload = json.loads(info.call_args.args[0])
    assert payload["event"] == "http_request"
    assert payload["method"] == "GET"
    assert payload["path"] == "/api/vehicles/{id}/track"
    assert payload["status"] == 200
    assert payload["duration_ms"] == 12.345
    assert payload["timestamp"].endswith("+00:00")


def test_cache_lookup_log_contains_operation_and_result():
    with patch("auto_parking.observability.performance.logger.info") as info:
        log_cache_lookup(
            operation="vehicle_track_payload",
            result="hit",
            duration_seconds=0.001234,
        )

    payload = json.loads(info.call_args.args[0])
    assert payload["event"] == "cache_lookup"
    assert payload["operation"] == "vehicle_track_payload"
    assert payload["result"] == "hit"
    assert payload["duration_ms"] == 1.234


def test_access_log_is_goaccess_parseable_and_redacts_query_tokens():
    request = SimpleNamespace(
        method="GET",
        url=URL("http://test/api/notifications/ws?token=secret&format=json"),
        headers=Headers(
            {
                "referer": "http://localhost/",
                "user-agent": "pytest",
                "x-forwarded-for": "203.0.113.7, 10.0.0.1",
            }
        ),
        client=SimpleNamespace(host="127.0.0.1"),
        scope={"http_version": "1.1", "time": 1780738445},
    )

    with patch("auto_parking.observability.access_log.logger.info") as info:
        log_access_request(
            request=request,
            status=404,
            bytes_sent=22,
            duration_seconds=0.012345,
        )

    assert info.call_args.args == (
        '%s - - [%s] "%s" %s %s "%s" "%s" %s',
        "203.0.113.7",
        1780738445,
        "GET /api/notifications/ws?token=REDACTED&format=json HTTP/1.1",
        404,
        22,
        "http://localhost/",
        "pytest",
        12.345,
    )
