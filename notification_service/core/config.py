from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    debug: bool = Field(default=False, alias="DEBUG")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    kafka_bootstrap_servers: str | None = Field(
        default=None,
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
