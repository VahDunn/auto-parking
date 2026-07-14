from __future__ import annotations

from time import perf_counter
from typing import Any

from prometheus_client import Counter, Histogram
from sqlalchemy import event
from sqlalchemy.engine import ExceptionContext
from sqlalchemy.exc import (
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
    TimeoutError,
)
from sqlalchemy.ext.asyncio import AsyncEngine

SQL_EVENTS_TOTAL = Counter(
    "auto_parking_sql_events_total",
    "SQL errors and PostgreSQL server messages observed by the API.",
    ("severity", "operation", "category"),
)
SQL_EVENTS_BY_SEVERITY_TOTAL = Counter(
    "auto_parking_sql_events_by_severity_total",
    "SQL errors and PostgreSQL server messages grouped by severity.",
    ("severity",),
)
SQL_QUERY_DURATION_SECONDS = Histogram(
    "auto_parking_sql_query_duration_seconds",
    "SQL query duration in seconds.",
    ("operation",),
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

_OBSERVED_SEVERITIES = frozenset({"WARNING", "ERROR", "FATAL", "PANIC"})
_KNOWN_OPERATIONS = frozenset({"SELECT", "INSERT", "UPDATE", "DELETE", "CONNECT"})
_TIMER_ATTRIBUTE = "_auto_parking_sql_started_at"

for _severity in _OBSERVED_SEVERITIES:
    SQL_EVENTS_BY_SEVERITY_TOTAL.labels(severity=_severity).inc(0)


def setup_database_metrics(engine: AsyncEngine) -> None:
    """Attach bounded-cardinality SQL metrics to the application's engine once."""

    sync_engine = engine.sync_engine
    listeners = (
        ("before_cursor_execute", _before_cursor_execute),
        ("after_cursor_execute", _after_cursor_execute),
        ("handle_error", _handle_error),
        ("connect", _on_connect),
    )
    for event_name, listener in listeners:
        if not event.contains(sync_engine, event_name, listener):
            event.listen(sync_engine, event_name, listener)


def _before_cursor_execute(
    connection: Any,
    cursor: Any,
    statement: str,
    parameters: Any,
    context: Any,
    executemany: bool,
) -> None:
    del connection, cursor, statement, parameters, executemany
    setattr(context, _TIMER_ATTRIBUTE, perf_counter())


def _after_cursor_execute(
    connection: Any,
    cursor: Any,
    statement: str,
    parameters: Any,
    context: Any,
    executemany: bool,
) -> None:
    del connection, cursor, parameters, executemany
    _observe_query_duration(context, statement)


def _handle_error(context: ExceptionContext) -> None:
    statement = context.statement or ""
    _observe_query_duration(context.execution_context, statement)

    error = context.sqlalchemy_exception or context.original_exception
    severity = _error_severity(error)
    SQL_EVENTS_TOTAL.labels(
        severity=severity,
        operation=_sql_operation(statement),
        category=_error_category(error),
    ).inc()
    SQL_EVENTS_BY_SEVERITY_TOTAL.labels(severity=severity).inc()


def _on_connect(dbapi_connection: Any, connection_record: Any) -> None:
    del connection_record
    driver_connection = getattr(dbapi_connection, "driver_connection", None)
    add_log_listener = getattr(driver_connection, "add_log_listener", None)
    if callable(add_log_listener):
        add_log_listener(_on_postgres_message)


def _on_postgres_message(connection: Any, message: Any) -> None:
    del connection
    severity = _normalize_severity(
        getattr(message, "severity_en", None) or getattr(message, "severity", None)
    )
    if severity not in _OBSERVED_SEVERITIES:
        return

    SQL_EVENTS_TOTAL.labels(
        severity=severity,
        operation="OTHER",
        category="server_message",
    ).inc()
    SQL_EVENTS_BY_SEVERITY_TOTAL.labels(severity=severity).inc()


def _observe_query_duration(context: Any, statement: str) -> None:
    if context is None:
        return
    started_at = getattr(context, _TIMER_ATTRIBUTE, None)
    if started_at is None:
        return
    delattr(context, _TIMER_ATTRIBUTE)
    SQL_QUERY_DURATION_SECONDS.labels(operation=_sql_operation(statement)).observe(
        max(0.0, perf_counter() - started_at)
    )


def _sql_operation(statement: str | None) -> str:
    if not statement:
        return "CONNECT"
    operation = statement.lstrip().split(maxsplit=1)[0].upper() if statement.strip() else "OTHER"
    return operation if operation in _KNOWN_OPERATIONS else "OTHER"


def _error_severity(error: BaseException) -> str:
    for candidate in _exception_chain(error):
        severity = _normalize_severity(
            getattr(candidate, "severity_en", None) or getattr(candidate, "severity", None)
        )
        if severity in _OBSERVED_SEVERITIES:
            return severity
    return "ERROR"


def _error_category(error: BaseException) -> str:
    for candidate in _exception_chain(error):
        if isinstance(candidate, IntegrityError) or "integrity" in type(candidate).__name__.lower():
            return "integrity"
        if isinstance(candidate, TimeoutError) or "timeout" in type(candidate).__name__.lower():
            return "timeout"
        if isinstance(candidate, OperationalError):
            return "operational"
        if isinstance(candidate, ProgrammingError):
            return "programming"
        if isinstance(candidate, DataError):
            return "data"

        name = type(candidate).__name__.lower()
        if any(part in name for part in ("connection", "interface", "cannotconnect")):
            return "connection"
        if "syntax" in name or "undefined" in name:
            return "programming"
    return "other"


def _exception_chain(error: BaseException):
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        nested = getattr(current, "orig", None) or current.__cause__ or current.__context__
        current = nested if isinstance(nested, BaseException) else None


def _normalize_severity(value: Any) -> str:
    return str(value or "").upper()
