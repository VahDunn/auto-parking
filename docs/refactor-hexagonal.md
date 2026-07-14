# Рефакторинг `auto_parking/` под гексагональную структуру

## Context

Сейчас `auto_parking/` — плоский пакет, в котором в одном корне лежат:
- слои основного монолита (`api/`, `service/`, `repo/`, `filter/`, `deps/`, `ports/`, `db/`, `integrations/`, `observability/`, `realtime/`);
- отдельный сервис Telegram-бота (`bot/`);
- скрипты (`minor_utilities/`);
- cross-cutting (`core/`) и entrypoint (`main.py`).

Границы слоёв монолита неявны и путаются с сервисами-соседями. Задача — вычленить монолит в две подсистемы (`app/` — application-layer, `infrastructure/` — адаптеры) под гексагональную архитектуру, оставив `core/`, `bot/`, `minor_utilities/`, `main.py` на месте. Другие сервисы (`audit_service`, `notification_service`, `event_bus`) не импортируют из `auto_parking.*` — их не трогаем.

Репозитории переезжают в `infrastructure/db/repositories/` **без** введения абстрактных портов (по явному решению — минимизируем объём диффа).

## Целевая структура

```
auto_parking/
├── main.py                          # без изменений
├── core/                            # без изменений (config, security, errors, handlers, logger, domain, utils)
├── bot/                             # без изменений
├── minor_utilities/                 # без изменений
│
├── app/
│   ├── __init__.py                  # новый
│   ├── api/                         # из auto_parking/api/ (router.py + v1/)
│   ├── schemas/                     # из auto_parking/api/schemas/  ← выносится ИЗ api/
│   ├── service/                     # из auto_parking/service/
│   ├── filter/                      # из auto_parking/filter/
│   ├── deps/                        # из auto_parking/deps/
│   └── ports/                       # из auto_parking/ports/ (cache, events, geocoding)
│
└── infrastructure/
    ├── __init__.py                  # новый
    ├── db/
    │   ├── __init__.py              # новый
    │   ├── engine.py                # из auto_parking/db/engine.py
    │   ├── admin.py                 # из auto_parking/db/admin.py
    │   ├── events.py                # из auto_parking/db/events.py
    │   ├── models/                  # из auto_parking/db/models/
    │   └── repositories/            # из auto_parking/repo/  (файлы 1:1)
    ├── cache/                       # из auto_parking/integrations/cache/
    ├── events/                      # из auto_parking/integrations/events/
    ├── geocoding/                   # из auto_parking/integrations/geocoding/
    ├── observability/               # merge: auto_parking/observability/ + auto_parking/integrations/monitoring/
    │   ├── __init__.py              # объединить re-export'ы обоих старых __init__.py
    │   ├── access_log.py
    │   ├── performance.py
    │   ├── database.py              # ex-integrations/monitoring/
    │   ├── prometheus.py            # ex-integrations/monitoring/
    │   └── tracing.py               # ex-integrations/monitoring/
    └── realtime/                    # из auto_parking/realtime/
```

## Объём

- 75 `.py` файлов переезжают (без учёта `__pycache__`).
- ~403 import-строк требуют переписывания (в ~130 файлах: `auto_parking/**`, `tests/**`, `alembic/env.py`).
- 2 конфиг-файла: `pyproject.toml` (строка 92, `[tool.pyright] exclude`), `alembic/env.py` (строка 10).
- `Dockerfile`, `docker-compose*.yaml`, `deploy/docker-compose.prod.yaml`, `.github/workflows/ci.yml`, `alembic.ini`, `mypy.ini` — модуль-пути внутри них ссылаются только на `main`, `bot`, `minor_utilities`, которые не переезжают. Правок не требуется.
- Sibling-сервисы (`audit_service/`, `notification_service/`, `event_bus/`, `load_tests/`) не импортируют из `auto_parking.*` — не трогаем.

## Мэппинг import-путей (шаблон переписывания)

```
auto_parking.api.schemas.*   →  auto_parking.app.schemas.*
auto_parking.api.*           →  auto_parking.app.api.*
auto_parking.service.*       →  auto_parking.app.service.*
auto_parking.filter.*        →  auto_parking.app.filter.*
auto_parking.deps.*          →  auto_parking.app.deps.*
auto_parking.ports.*         →  auto_parking.app.ports.*

auto_parking.repo.*                        →  auto_parking.infrastructure.db.repositories.*
auto_parking.db.*                          →  auto_parking.infrastructure.db.*
auto_parking.integrations.cache.*          →  auto_parking.infrastructure.cache.*
auto_parking.integrations.events.*         →  auto_parking.infrastructure.events.*
auto_parking.integrations.geocoding.*      →  auto_parking.infrastructure.geocoding.*
auto_parking.integrations.monitoring.*     →  auto_parking.infrastructure.observability.*
auto_parking.observability.*               →  auto_parking.infrastructure.observability.*
auto_parking.realtime.*                    →  auto_parking.infrastructure.realtime.*

auto_parking.core.*, .bot.*, .main, .minor_utilities.*  —  БЕЗ ИЗМЕНЕНИЙ
```

**Порядок применения** имеет значение: сначала более длинный префикс (`api.schemas` → `app.schemas`), потом короткий (`api` → `app.api`). Аналогично для `integrations.monitoring` перед `integrations.*` и для `db.models` — попадает под общий шаблон `db.* → infrastructure.db.*` (перезаписей не требуется отдельно, регекс покрывает).

## Порядок исполнения

1. **Создать каркас** `auto_parking/app/`, `auto_parking/infrastructure/`, `infrastructure/db/`, каждый с `__init__.py`.
2. **Перенести директории** через `git mv` для сохранения истории:
   - `git mv auto_parking/api/schemas auto_parking/app/schemas`
   - `git mv auto_parking/api auto_parking/app/api`
   - `git mv auto_parking/service auto_parking/app/service`
   - `git mv auto_parking/filter auto_parking/app/filter`
   - `git mv auto_parking/deps auto_parking/app/deps`
   - `git mv auto_parking/ports auto_parking/app/ports`
   - `git mv auto_parking/db/engine.py auto_parking/infrastructure/db/engine.py` (и `admin.py`, `events.py`)
   - `git mv auto_parking/db/models auto_parking/infrastructure/db/models`
   - `git mv auto_parking/repo auto_parking/infrastructure/db/repositories`
   - `git mv auto_parking/integrations/cache auto_parking/infrastructure/cache`
   - `git mv auto_parking/integrations/events auto_parking/infrastructure/events`
   - `git mv auto_parking/integrations/geocoding auto_parking/infrastructure/geocoding`
   - `git mv auto_parking/realtime auto_parking/infrastructure/realtime`
   - Отдельные файлы `integrations/monitoring/{database,prometheus,tracing}.py` и `observability/{access_log,performance}.py` — `git mv` каждый в `auto_parking/infrastructure/observability/`.
   - Удалить пустые `auto_parking/db/`, `auto_parking/integrations/`, `auto_parking/observability/` (их `__init__.py` больше не нужны).
3. **Смержить `__init__.py` observability**: сложить re-export'ы из `auto_parking/observability/__init__.py` и `auto_parking/integrations/monitoring/__init__.py` в новый `auto_parking/infrastructure/observability/__init__.py`.
4. **Переписать импорты** во всех `.py` через `find + sed` по регексам из таблицы выше. Затрагиваются:
   - `auto_parking/**` (все переехавшие модули + `main.py`, `core/`, `bot/`, `minor_utilities/`)
   - `tests/**` (~40 файлов)
   - `alembic/env.py` (одна строка: `auto_parking.db.models → auto_parking.infrastructure.db.models`)
5. **Обновить конфиги**:
   - `pyproject.toml` L92: `'auto_parking/db/admin.py'` → `'auto_parking/infrastructure/db/admin.py'`.
6. **Прогнать проверки**: см. Verification.

## Известные архитектурные шероховатости (не чиним в этом рефакторе)

- `app/api/v1/live_tracking.py` импортирует `auto_parking.repo.user.UserRepository` — layer-skip (API → repo, минуя service). Существующая аномалия; после переезда путь станет `auto_parking.infrastructure.db.repositories.user`. Работоспособность не теряется.
- 7 файлов в `repo/` импортируют из `filter/`. После переезда это станет `infrastructure → app` — формально нарушение гексагона. Оставляем как есть: `filter` — query-DTO, реальной цикличности нет, изоляция для этого рефакторинга избыточна.

## Verification

1. **Импорты собираются**: `poetry run python -c "import auto_parking.main; import auto_parking.bot.main; import auto_parking.app.api.router; import auto_parking.infrastructure.db.models"` — без `ImportError`.
2. **Статическая проверка**: `poetry run ruff check auto_parking tests alembic` — должно пройти без ошибок E/F/I.
3. **mypy**: `poetry run mypy auto_parking` — сравнить кол-во ошибок с базой до рефакторинга (регресса быть не должно).
4. **Тесты**: `poetry run pytest tests/unit -q` — все прежние unit-тесты зелёные (интеграционные требуют Postgres/Redis/Kafka, их не гоняем в plan-подтверждении).
5. **Приложение стартует**: `poetry run uvicorn auto_parking.main:app --port 8000` — старт без ошибок, `curl localhost:8000/docs` открывается.
6. **Alembic**: `poetry run alembic upgrade head --sql` — генерация SQL без ошибок (проверяет, что модели видны из `auto_parking.infrastructure.db.models`).
7. **Git-история сохранена**: `git log --follow auto_parking/app/service/vehicle.py` показывает историю до переезда (за счёт `git mv`).
