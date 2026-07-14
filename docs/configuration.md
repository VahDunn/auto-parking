# Конфигурация

Приложение получает настройки из переменных окружения. Этот документ описывает
их назначение; актуальные имена и значения по умолчанию определены в коде и
Compose-файлах.

## Шаблоны окружений

| Окружение | Шаблон | Оркестрация |
| --- | --- | --- |
| Локальное | [`.env.example`](../.env.example) | [`docker-compose.yaml`](../docker-compose.yaml) |
| Production | [`deploy/.env.prod.example`](../deploy/.env.prod.example) | [`deploy/docker-compose.prod.yaml`](../deploy/docker-compose.prod.yaml) |

Скопированный `.env` содержит секреты и не должен попадать в Git. Значения,
переданные процессу напрямую, имеют приоритет над файлом `.env`; явный блок
`environment` в Compose имеет приоритет над `env_file`.

## Основные группы

| Группа | Основные переменные | Назначение |
| --- | --- | --- |
| Основная БД | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL` | PostgreSQL/PostGIS основного API и Alembic |
| Audit БД | `AUDIT_POSTGRES_DB`, `AUDIT_POSTGRES_USER`, `AUDIT_POSTGRES_PASSWORD`, `AUDIT_DATABASE_URL` | Отдельное хранилище `audit-service` |
| Авторизация | `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TTL_MINUTES` | Подпись и срок жизни access token |
| Интеграции | `REDIS_URL`, `KAFKA_BOOTSTRAP_SERVERS` | Cache/session registry и event bus |
| Telegram | `TELEGRAM_BOT_TOKEN` | Профили `bot` и `notifications` |
| Alerting | `ALERT_TELEGRAM_CHAT_ID`, `TELEGRAM_BOT_TOKEN` | Docker secrets для Alertmanager |

`DATABASE_URL` внутри Compose должен использовать имя сервиса `db`, а не
`localhost`. Для локального процесса вне Docker укажите адрес, доступный с host.
Production Compose собирает `AUDIT_DATABASE_URL` из трёх `AUDIT_POSTGRES_*`;
явный URL нужен при запуске audit-service вне Compose и в тестах.

## Настройки приложения

Канонический список находится в
[`auto_parking/core/config.py`](../auto_parking/core/config.py). Наиболее важные
группы:

- `APP_ENV`, `DEBUG`, `LOG_LEVEL` — режим и логирование;
- `ENTITY_CACHE_TTL_SECONDS`, `VEHICLE_MODEL_CACHE_TTL_SECONDS`,
  `VEHICLE_TRACK_CACHE_TTL_SECONDS` — TTL cache;
- `GPS_CONSUMER_ENABLED` — Kafka consumer live GPS;
- `OUTBOX_DISPATCHER_*` — batch, polling и retry transactional outbox;
- `PERFORMANCE_LOG_*`, `APP_ACCESS_LOG_PATH` — локальные JSONL/access logs;
- `OTEL_*` — трассировка, endpoint, sampling и исключённые URL.

Настройки отдельных процессов определены в
[`notification_service/core/config.py`](../notification_service/core/config.py)
и [`audit_service/core/config.py`](../audit_service/core/config.py).

## Секреты

В Git нельзя сохранять:

- production-пароли БД и `JWT_SECRET_KEY`;
- Telegram token и chat ID;
- SSH private key и GHCR token;
- реальные `.env` файлы.

В локальном окружении допустимы демонстрационные значения из `.env.example`.
Production `.env` создаётся непосредственно на сервере; GitHub Actions получает
только секреты, необходимые для SSH и скачивания images. Подробности разделены
между [CI/CD](ci-cd.md) и [деплоем](deployment.md).

## Проверка

Проверить подстановку Compose без запуска контейнеров:

```bash
docker compose config --quiet
```

Команда раскрывает значения переменных, поэтому её полный вывод нельзя
публиковать в issue, CI log или чате без предварительной очистки секретов.
