# Тестирование

Точка входа для проверок проекта. Здесь описаны слои
тестов, команды `pytest` и фактические проверки CI. Специализированные сценарии
вынесены отдельно:

- [браузерные E2E-тесты](e2e.md);
- [нагрузочное тестирование](load-testing.md);

## Слои тестов

| Слой | Расположение | Что проверяет | Внешняя инфраструктура |
| --- | --- | --- | --- |
| Unit | `tests/unit/` | сервисы, фильтры, транзакции, bot, cache, metrics и tracing с mock/fake-зависимостями | не нужна |
| Controller | `tests/controllers/` | FastAPI HTTP/WebSocket-контракты через in-process ASGI-клиент и dependency overrides | не нужна |
| Integration | `tests/integration/` | API, ORM, PostGIS, миграции, outbox и межсервисный event flow | отдельный PostgreSQL/PostGIS |
| Browser E2E | `tests/e2e/` | frontend, Nginx и API в Chromium | отдельный Docker Compose-стенд |
| Prometheus rules | `monitoring/tests/alerts.test.yml` | срабатывание alert rules на синтетических рядах | `promtool` из Docker image |
| Load | `load_tests/locustfile.py` | пропускную способность и latency работающего стенда | поднятое приложение и тестовые данные |

Marker `integration` зарегистрирован в `pyproject.toml`. Если
`RUN_INTEGRATION` не равен `1`, collection hook помечает такие тесты как
пропущенные. У unit и controller тестов отдельных markers нет — они выбираются
по каталогам.

## Подготовка Python-окружения

Проект поддерживает Python `>=3.12,<4`; Docker images и GitHub Actions используют
Python 3.12. Установить приложение и dev-зависимости:

```bash
poetry install --with dev --no-interaction
```

При импорте приложения нужны валидные обязательные settings. Обычно они уже
заданы в локальном `.env`. Для чистого shell достаточно тестовых значений:

```bash
export APP_ENV=test
export DATABASE_URL=postgresql+asyncpg://auto_parking:change-me@127.0.0.1:55432/auto_parking_test
export AUDIT_DATABASE_URL="$DATABASE_URL"
export JWT_SECRET_KEY=test-secret
export KAFKA_BOOTSTRAP_SERVERS=""
export GPS_CONSUMER_ENABLED=false
export OTEL_TRACING_ENABLED=false
```

Для unit и controller тестов сервер по этому адресу не требуется: обращения к
БД и другим внешним системам подменены. Integration-тестам нужна реальная
отдельная БД, описанная ниже.

## Unit и controller тесты

Быстрая локальная проверка без внешней инфраструктуры:

```bash
poetry run pytest tests/unit tests/controllers
```

Слои можно запускать независимо:

```bash
poetry run pytest tests/unit
poetry run pytest tests/controllers
```

Обычная команда для всего Python-набора тоже безопасна без PostGIS, пока
`RUN_INTEGRATION` не равен `1`: integration-тесты будут собраны и пропущены.

```bash
poetry run pytest tests
```

Для точечного запуска передайте путь к файлу или test node:

```bash
poetry run pytest tests/unit/services/test_vehicle_service.py
poetry run pytest \
  tests/controllers/test_vehicles.py::test_get_vehicles_builds_filter_and_respects_visibility
```

## Integration-тесты

> Integration fixture удаляет и заново создаёт таблицы перед каждым тестом, а
> тест миграций пересоздаёт schema `public`. Никогда не указывайте рабочую или
> общую локальную БД.

Поднять одноразовый PostGIS-контейнер:

```bash
docker run --rm -d --name auto-parking-it-postgis \
  -e POSTGRES_DB=auto_parking_test \
  -e POSTGRES_USER=auto_parking \
  -e POSTGRES_PASSWORD=change-me \
  -p 55432:5432 \
  postgis/postgis:16-3.4

until docker exec auto-parking-it-postgis \
  pg_isready -U auto_parking -d auto_parking_test; do
  sleep 1
done
```

Запустить integration-набор:

```bash
RUN_INTEGRATION=1 \
TEST_DATABASE_URL=postgresql+asyncpg://auto_parking:change-me@127.0.0.1:55432/auto_parking_test \
DATABASE_URL=postgresql+asyncpg://auto_parking:change-me@127.0.0.1:55432/auto_parking_test \
AUDIT_DATABASE_URL=postgresql+asyncpg://auto_parking:change-me@127.0.0.1:55432/auto_parking_test \
JWT_SECRET_KEY=test-secret \
KAFKA_BOOTSTRAP_SERVERS="" \
GPS_CONSUMER_ENABLED=false \
OTEL_TRACING_ENABLED=false \
poetry run pytest tests/integration
```

После прогона удалить контейнер:

```bash
docker stop auto-parking-it-postgis
```

Integration-тесты используют настоящий Postgres/PostGIS, но не требуют Kafka,
Redis или Telegram: соответствующие границы заменены in-memory/fake-реализациями.

## Prometheus rule tests

Файл `monitoring/tests/alerts.test.yml` проверяется отдельным `promtool` image.
Compose-контейнер Prometheus не монтирует каталог с тестами, поэтому команда
запускает одноразовый контейнер:

```bash
docker run --rm \
  -v "$PWD/monitoring:/etc/prometheus/monitoring:ro" \
  --entrypoint promtool \
  prom/prometheus:v2.55.1 \
  test rules /etc/prometheus/monitoring/tests/alerts.test.yml
```

Эта проверка нужна после изменения `monitoring/alerts.yml` или самих rule tests.
GitHub Actions её сейчас не запускает.

## Lint, format, type checking и coverage

Единственный обязательный статический gate в текущем CI и локальном commit hook:

```bash
poetry run ruff check .
```

Ruff formatter настроен, но format check не входит в CI. Его можно запускать
вручную:

```bash
poetry run ruff format --check .
```

`mypy` присутствует в dev-зависимостях, а в `pyproject.toml` есть настройки
Pyright, но ни один type checker не является CI gate. Канонический type-check
workflow пока не настроен. Coverage-инструмент, порог и публикация отчёта также
отсутствуют; команда `pytest` не измеряет покрытие.

## Что запускает CI

Job `checks` в `.github/workflows/ci.yml` выполняется на каждый push и pull
request. Он поднимает PostGIS service container, задаёт `RUN_INTEGRATION=1` и
запускает:

```bash
poetry install --with dev --no-interaction
poetry run ruff check .
poetry run pytest tests
```

Таким образом, CI запускает unit, controller и integration тесты. Он не
запускает browser E2E, Prometheus rule tests, Locust, coverage, type checking и
Ruff format check.

## Выбор проверки перед pull request

| Изменение | Минимальная релевантная проверка |
| --- | --- |
| Python-код | Ruff + unit/controller tests |
| ORM, repository, Alembic, PostGIS | дополнительно integration tests |
| HTTP-контракт или frontend | дополнительно browser E2E |
| Alert rules | дополнительно `promtool test rules` |
| Производительность критического пути | выбранный Locust-профиль на отдельном стенде |

Нагрузочные и мутационные browser-тесты запускайте только на специально
подготовленных данных. Их ограничения и cleanup описаны в соответствующих
руководствах.
