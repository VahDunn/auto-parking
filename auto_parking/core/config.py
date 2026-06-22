from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings  # pyright: ignore[reportMissingImports]

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    app_env: str = Field(default="dev", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")

    database_url: str = Field(..., alias="DATABASE_URL")
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_ttl_minutes: int = Field(default=30, alias="JWT_ACCESS_TTL_MINUTES")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    performance_log_path: str = Field(
        default="logs/performance.jsonl",
        alias="PERFORMANCE_LOG_PATH",
    )
    app_access_log_path: str = Field(
        default="logs/app-access.log",
        alias="APP_ACCESS_LOG_PATH",
    )
    performance_log_max_bytes: int = Field(
        default=10 * 1024 * 1024,
        alias="PERFORMANCE_LOG_MAX_BYTES",
    )
    performance_log_backup_count: int = Field(default=5, alias="PERFORMANCE_LOG_BACKUP_COUNT")
    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    bot_api_base_url: str = Field(default="http://localhost:8000/api", alias="BOT_API_BASE_URL")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    bot_summary_cache_ttl_seconds: int = Field(default=300, alias="BOT_SUMMARY_CACHE_TTL_SECONDS")
    bot_login_registry_ttl_seconds: int = Field(
        default=7 * 24 * 60 * 60,
        alias="BOT_LOGIN_REGISTRY_TTL_SECONDS",
    )
    event_bus_backend: str = Field(default="redis", alias="EVENT_BUS_BACKEND")
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        alias="KAFKA_BOOTSTRAP_SERVERS",
    )
    kafka_notification_consumer_group: str = Field(
        default="auto-parking-notification-service",
        alias="KAFKA_NOTIFICATION_CONSUMER_GROUP",
    )
    entity_cache_ttl_seconds: int = Field(default=300, alias="ENTITY_CACHE_TTL_SECONDS")
    vehicle_model_cache_ttl_seconds: int = Field(
        default=3600,
        alias="VEHICLE_MODEL_CACHE_TTL_SECONDS",
    )
    vehicle_track_cache_ttl_seconds: int = Field(
        default=300,
        alias="VEHICLE_TRACK_CACHE_TTL_SECONDS",
    )
    model_config = {
        "env_file": str(ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
