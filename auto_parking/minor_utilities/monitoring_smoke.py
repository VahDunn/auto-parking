from __future__ import annotations

import argparse
import asyncio

import httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from auto_parking.infrastructure.db.engine import engine
from auto_parking.infrastructure.observability.database import setup_database_metrics

_MISSING_ROUTE = "/api/__monitoring_smoke_missing__"
_MISSING_TABLE_QUERY = "SELECT * FROM auto_parking_monitoring_smoke_missing_table"


def generate_http_404(*, base_url: str, count: int) -> list[int]:
    """Generate recognizable, read-only interservice 404 responses."""

    with httpx.Client(
        base_url=base_url.rstrip("/"),
        headers={"X-Auto-Parking-Service": "telegram-bot"},
        timeout=10,
    ) as client:
        return [client.get(_MISSING_ROUTE).status_code for _ in range(count)]


async def generate_sql_errors(*, count: int) -> int:
    """Run an invalid SELECT and swallow the expected exceptions."""

    setup_database_metrics(engine)
    observed = 0
    try:
        for _ in range(count):
            try:
                async with engine.connect() as connection:
                    await connection.execute(text(_MISSING_TABLE_QUERY))
            except SQLAlchemyError:
                observed += 1
    finally:
        await engine.dispose()
    return observed


async def generate_slow_sql(*, count: int, delay_seconds: float) -> int:
    """Generate safe SELECT latency for checking the SQL p95 panels."""

    setup_database_metrics(engine)
    try:
        for _ in range(count):
            async with engine.connect() as connection:
                await connection.execute(
                    text("SELECT pg_sleep(:delay_seconds)"),
                    {"delay_seconds": delay_seconds},
                )
    finally:
        await engine.dispose()
    return count


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate safe monitoring smoke-test signals.")
    parser.add_argument("scenario", choices=("http-404", "sql-error", "sql-latency"))
    parser.add_argument("--count", type=_positive_int, default=3)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--delay-seconds", type=_non_negative_float, default=0.3)
    args = parser.parse_args()

    if args.scenario == "http-404":
        statuses = generate_http_404(base_url=args.base_url, count=args.count)
        print(f"generated={len(statuses)} statuses={statuses}")
        return

    if args.scenario == "sql-error":
        observed = asyncio.run(generate_sql_errors(count=args.count))
        print(f"generated={observed} expected_sql_errors")
        return

    observed = asyncio.run(generate_slow_sql(count=args.count, delay_seconds=args.delay_seconds))
    print(f"generated={observed} slow_sql_queries delay_seconds={args.delay_seconds}")


if __name__ == "__main__":
    main()
