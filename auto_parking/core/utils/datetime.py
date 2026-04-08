from datetime import UTC, datetime
from zoneinfo import ZoneInfo


def ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("Naive datetime is not allowed")
    return dt


def to_utc(dt: datetime) -> datetime:
    dt = ensure_aware(dt)
    return dt.astimezone(UTC)


def to_enterprise_tz(dt_utc: datetime, tz_name: str | None) -> datetime:
    dt_utc = ensure_aware(dt_utc)
    tz = ZoneInfo(tz_name or "UTC")
    return dt_utc.astimezone(tz)