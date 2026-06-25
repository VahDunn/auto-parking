from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    debug: bool = Field(default=False, alias="DEBUG")
    database_url: str = Field(alias="AUDIT_DATABASE_URL")
    kafka_bootstrap_servers: str | None = Field(
        default=None,
        alias="KAFKA_BOOTSTRAP_SERVERS",
    )
    kafka_audit_source_consumer_group: str = Field(
        default="auto-parking-audit-service",
        alias="KAFKA_AUDIT_SOURCE_CONSUMER_GROUP",
    )

    model_config = {
        "env_file": str(ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
