# Структура проекта Auto Parking

Документ описывает актуальную структуру проекта и границы ответственности слоев.

## Общая схема

```text
FastAPI controllers
  -> services/use cases
    -> repositories
      -> SQLAlchemy models

services
  -> ports
    -> integrations
```

Главное правило: HTTP-слой не лезет напрямую в БД, репозитории не знают про FastAPI, внешняя инфраструктура подключается через `ports` и `integrations`.

## Корень проекта

```text
auto_parking/       backend-приложение
notification_service/ отдельный микросервис уведомлений
frontend/           статический web-интерфейс
alembic/            миграции БД
monitoring/         GoAccess, Prometheus, Grafana-конфиги
load_tests/         Locust-сценарии нагрузочного тестирования
logs/               локальные логи и отчеты, не часть кода
```

## Backend

```text
auto_parking/
  api/              FastAPI routes и Pydantic API schemas
  bot/              Telegram bot process, сейчас ходит в основной API по HTTP
  core/             настройки, безопасность, доменные модели и enums
  db/               SQLAlchemy engine, session, ORM-модели
  deps/             FastAPI dependencies и сборка сервисов
  filter/           внутренние фильтры для сервисов и репозиториев
  integrations/     конкретные адаптеры внешней инфраструктуры
  minor_utilities/  утилиты и генераторы, включая live track generator
  observability/    access/performance logging
  ports/            абстрактные контракты внешних зависимостей
  realtime/         live GPS поток, Redis pub/sub, RxPY pipeline, WebSocket broadcast
  repo/             SQLAlchemy repositories
  service/          бизнес-сценарии и orchestration
  main.py           точка входа FastAPI
```

## API слой

`auto_parking/api/v1` содержит контроллеры ресурсов:

```text
auth.py
drivers.py
notifications.py
vehicle_models.py
enterprises/
reports/
vehicles/
```

Контроллеры отвечают за HTTP-детали: path/query/body, `Depends`, статусы, `HTTPException`, преобразование доменных моделей в API-схемы. Бизнес-правила и работа с БД должны оставаться в сервисах и репозиториях.

## Service слой

`auto_parking/service` содержит сценарии приложения: CRUD-правила, visibility, импорт/экспорт, отчеты, треки, поездки, уведомления. Сервисы работают с доменными моделями и фильтрами, а не с Pydantic API DTO.

Сервис может координировать несколько репозиториев и вызывать внешнюю инфраструктуру только через небольшой порт или уже принятый адаптер.

Важно: `auto_parking/service/notification.py` - это внутренний application service основного API для REST/WebSocket уведомлений. Отдельный микросервис уведомлений находится в top-level пакете `notification_service/`.

## Repo слой

`auto_parking/repo` содержит SQLAlchemy-запросы, фильтрацию, загрузку relation-ов, создание и обновление ORM-сущностей. Репозиторий не должен содержать бизнес-логику, HTTP-ошибки, API-схемы и форматирование ответа.

Для списочных чтений основной контракт: `get(filter_obj)`. Разные сценарии поиска выражаются полями фильтра, а не набором ad hoc методов.

## Ports и integrations

`auto_parking/ports` хранит абстракции внешней инфраструктуры. Сейчас там есть cache/geocoding contracts и event bus contracts:

```text
CacheClient
ReverseGeocoder
EventProducer
EventConsumer
```

`auto_parking/integrations` хранит конкретные реализации портов: Redis cache, Geoapify, monitoring, Kafka/Redis event adapters.

## Realtime и уведомления

Сейчас live GPS устроен так:

```text
track_generator -> Redis pub/sub -> realtime/gps.py -> RxPY pipeline -> WebSocket clients
```

Уведомления о поездках сейчас создаются внутри основного API и доставляются в websocket через in-memory publisher. Это работает локально, но плохо масштабируется на несколько workers и отдельные сервисы, потому что подключения живут в памяти конкретного процесса.

Для CRUD машин уже добавлен общий event bus. `VehicleService` публикует `vehicle.created/updated/deleted`, а отдельный top-level микросервис `notification_service` читает эти события из Kafka/Redis и отправляет Telegram-сообщения менеджерам, которые логинились в боте.

Kafka и Redis реализации подключаются через один порт. Переключатель:

```text
EVENT_BUS_BACKEND=kafka|redis|none
```

Микросервис уведомлений находится не внутри `auto_parking`, а в отдельном каталоге `notification_service/`. В Docker Compose он собирается отдельным Dockerfile.

## Frontend

`frontend/app` содержит статический интерфейс, стили и JavaScript-код. Основные frontend-модули лежат в `frontend/app/js`:

```text
api/       HTTP-клиент
app/       сборка экранов и состояние
features/  отдельные фичи
ui/        общие UI-компоненты
```

Frontend обращается к backend через публичный REST/WebSocket API и не должен знать о внутренней структуре сервисов.

## Нагрузочные тесты и мониторинг

`load_tests/locustfile.py` содержит сценарии Locust для healthcheck, чтения, записи и смешанной нагрузки.

`monitoring/goaccess` содержит конфиги GoAccess для чтения access logs приложения и nginx. `monitoring/prometheus.yml` подключает Prometheus scrape config.

## Правила для новых изменений

1. Контроллеры держать тонкими.
2. Бизнес-логику помещать в `service`.
3. SQL и relation loading держать в `repo`.
4. Redis, Kafka, Telegram и внешние API подключать через `ports/integrations`.
5. Для событий использовать общий envelope и абстрактные producer/consumer, чтобы backend можно было переключать.
6. Не добавлять agent/tooling файлы в git.
