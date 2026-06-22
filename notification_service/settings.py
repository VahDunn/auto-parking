from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    debug: bool = Field(default=False, alias="DEBUG")
    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    event_bus_backend: str = Field(default="kafka", alias="EVENT_BUS_BACKEND")
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        alias="KAFKA_BOOTSTRAP_SERVERS",
    )
    kafka_notification_consumer_group: str = Field(
        default="auto-parking-notification-service",
        alias="KAFKA_NOTIFICATION_CONSUMER_GROUP",
    )

    model_config = {
        "env_file": str(ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
