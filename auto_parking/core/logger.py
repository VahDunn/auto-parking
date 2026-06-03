import logging.config
from pathlib import Path

from auto_parking.core.config import settings


def get_logging_config():
    performance_log_path = Path(settings.performance_log_path)
    performance_log_path.parent.mkdir(parents=True, exist_ok=True)

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(name)s [%(levelname)s] %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "performance": {
                "format": "%(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
            "performance": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(performance_log_path),
                "maxBytes": settings.performance_log_max_bytes,
                "backupCount": settings.performance_log_backup_count,
                "encoding": "utf-8",
                "formatter": "performance",
            },
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["console"],
        },
        "loggers": {
            # убираем SQL спам
            "sqlalchemy.engine": {
                "level": "WARNING",
                "propagate": False,
            },
            # нормальные uvicorn логи
            "uvicorn": {
                "level": settings.log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.error": {
                "level": settings.log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": settings.log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            # httpx may include credentials from external API URLs in INFO logs.
            "httpx": {
                "level": "WARNING",
            },
            "auto_parking.performance": {
                "level": "INFO",
                "handlers": ["performance"],
                "propagate": False,
            },
        },
    }


def setup_logging():
    logging.config.dictConfig(get_logging_config())
