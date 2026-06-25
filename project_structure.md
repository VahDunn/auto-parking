# Структура проекта Auto Parking

Документ фиксирует текущую архитектуру проекта простыми слоями: runtime-процессы, общая библиотека событий, инфраструктура и основные потоки данных.

## Коротко

```text
auto_parking/          основной FastAPI-монолит
notification_service/ отдельный микросервис Telegram-уведомлений
audit_service/        отдельный микросервис аудита со своей БД
event_bus/            общая Python-библиотека для Kafka-событий, не микросервис
frontend/             статический frontend
nginx/                reverse proxy
```

Главное разделение:

```text
Сервисы приложения:
  auto-parking API
  telegram-bot
  notification-service
  audit-service

Общая библиотека:
  event_bus

Инфраструктура:
  PostgreSQL/PostGIS
  Redis
  Kafka
  Audit PostgreSQL
  nginx
  Prometheus/Grafana/GoAccess
```

## Runtime-Схема

```mermaid
flowchart TB
    Browser["Browser"] --> Nginx["nginx"]
    Nginx --> Frontend["frontend"]
    Nginx --> API["auto-parking API"]
    API --> Postgres["PostgreSQL/PostGIS"]
    API --> Redis["Redis<br/>cache"]
    API --> Kafka["Kafka"]

    TelegramUser["Telegram user"] --> TelegramBot["telegram-bot"]
    TelegramBot --> API
    TelegramBot --> Redis

    API -->|"vehicle.*"| Kafka
    API -->|"audit.*"| Kafka
    Kafka -->|"vehicle.*"| Notification["notification-service"]
    Notification -->|"audit.*"| Kafka
    Kafka -->|"audit.*"| Audit["audit-service"]
    Audit --> AuditDB["audit-db<br/>PostgreSQL"]

    Notification --> Redis
    Notification --> TelegramAPI["Telegram API"]
    TelegramAPI --> TelegramUser

    TrackGen["track_generator"] --> Postgres
    TrackGen -->|"vehicle.gps"| Kafka
    Kafka -->|"vehicle.gps"| API
    API -->|"WebSocket"| Browser
```

Что важно:

1. `Kafka` это отдельный брокер сообщений.
2. `event_bus/` это не сервис, а общая Python-библиотека, которую импортируют сервисы.
3. `Redis` не используется как брокер сообщений. Он нужен для cache и Telegram login registry.
4. `notification-service` не подключается к PostgreSQL основного приложения.
5. `audit-service` владеет своей БД `audit-db`; основной API в audit DB не пишет.

## Общая Библиотека Event Bus

`event_bus/` нужен, чтобы все сервисы одинаково понимали события и Kafka.

```text
event_bus/
  contracts.py     EventEnvelope, EventProducer, EventConsumer
  kafka.py         KafkaEventProducer, KafkaEventConsumer
  topics.py        единственное место описания Kafka topics
  init_topics.py   создание topics при старте docker-compose
```

Ее используют:

```text
auto_parking
notification_service
audit_service
```

Смысл:

```text
event_bus = общий код и контракт
Kafka     = реальный брокер сообщений
```

## Kafka Topics

Topics описаны только в [event_bus/topics.py](/Users/vl.morozov/PycharmProjects/auto-parking/event_bus/topics.py).

```text
auto-parking.vehicle.events  partitions=3  key=vehicle_id
auto-parking.audit.events    partitions=3  key=entity_id, fallback=event_id
auto-parking.gps.events      partitions=6  key=vehicle_id
```

`kafka-init` создает эти topics при запуске. `KAFKA_AUTO_CREATE_TOPICS_ENABLE=false`, чтобы Kafka не создавала topic-и случайно с дефолтными настройками.

Consumer groups:

```text
auto-parking-notification-service
auto-parking-audit-service
auto-parking-gps-live-<pid>-<uuid>
```

## Основной Монолит

```text
auto_parking/
  api/              HTTP/WebSocket routes и Pydantic schemas
  service/          бизнес-сценарии
  repo/             SQLAlchemy-запросы
  db/               engine, session, ORM-модели, SQLAdmin
  deps/             сборка зависимостей FastAPI
  ports/            re-export общих контрактов и протоколы внешних зависимостей
  integrations/     Redis cache, Kafka adapter re-export, Geoapify, Prometheus
  realtime/         live GPS consumer, RxPY pipeline, WebSocket broadcast
  bot/              Telegram bot code
  minor_utilities/  CLI-утилиты генерации машин и GPS-треков
  observability/    access/performance logging
```

Правила слоя:

1. Контроллеры не ходят напрямую в БД.
2. Бизнес-логика живет в `service/`.
3. SQL и relation loading живут в `repo/`.
4. Внешняя инфраструктура подключается через `ports/` и `integrations/`.

## Микросервисы

Оба микросервиса имеют упрощенную структуру:

```text
<service_name>/
  core/          settings
  ports/         протоколы внешних возможностей
  integrations/  Kafka/Redis/Telegram адаптеры по необходимости
  db/            собственные ORM-модели, engine и session, если сервис владеет БД
  repo/          SQLAlchemy-запись/чтение, если сервис владеет БД
  service/       обработка события
  main.py        composition root и запуск consumer-а
  Dockerfile     отдельный image
```

### notification_service

Назначение:

1. Читает `auto-parking.vehicle.events`.
2. Берет `manager_user_ids` из payload события.
3. По Redis login registry получает `telegram chat_id`.
4. Отправляет сообщение через Telegram API.
5. Публикует результат отправки в общий `auto-parking.audit.events`.

Схема:

```mermaid
flowchart LR
    Kafka["Kafka<br/>vehicle.events"] --> Main["notification_service/main.py"]
    Main --> Service["VehicleEventNotificationService"]
    Service --> Registry["RedisTelegramSessionRegistry"]
    Service --> Sender["TelegramBotSender"]
    Registry --> Redis["Redis"]
    Sender --> Telegram["Telegram API"]
    Service --> AuditTopic["Kafka<br/>audit.events"]
```

`notification_service` не импортирует `auto_parking.repo`, `auto_parking.service` и не подключается к PostgreSQL.

### audit_service

Назначение:

1. Читает общий `auto-parking.audit.events`.
2. Сохраняет событие в собственную PostgreSQL БД `audit-db`.
3. Не подключается к PostgreSQL основного приложения.

Схема:

```mermaid
flowchart LR
    Api["auto-parking API"] --> AuditTopic["Kafka<br/>audit.events"]
    Notification["notification_service"] --> AuditTopic
    AuditTopic --> AuditService["audit_service"]
    AuditService --> AuditDb["audit-db<br/>audit_event"]
```

## Основные Потоки

CRUD машины:

```text
HTTP request
-> VehicleService.create/update/delete
-> PostgreSQL commit
-> Kafka auto-parking.vehicle.events
-> Kafka auto-parking.audit.events
-> notification-service
```

Audit:

```text
auto-parking API / notification-service
-> Kafka auto-parking.audit.events
-> audit-service
-> audit-db audit_event
```

Live GPS:

```text
track_generator
-> PostgreSQL vehicle_gps_point / trip
-> Kafka auto-parking.gps.events
-> GpsRealtimeHub
-> RxPY filter/map/deduplicate pipeline
-> WebSocket clients
```

Telegram login:

```text
Telegram /login
-> telegram-bot
-> auto-parking API auth
-> Redis bot login registry
```

Telegram notification:

```text
Kafka vehicle event
-> notification-service
-> manager_user_ids из payload
-> Redis chat lookup
-> Telegram API
-> Kafka auto-parking.audit.events
```

## Docker Compose

Kafka-only режим для событий:

```text
kafka                 single-node broker
kafka-init            создает topics из event_bus/topics.py
audit-db              отдельная PostgreSQL БД audit-service
auto-parking          depends_on db, redis, kafka-init
telegram-bot          depends_on db, redis, kafka-init, auto-parking
notification-service  depends_on redis, kafka-init
audit-service         depends_on audit-db, kafka-init
```

В Docker Compose включен live GPS consumer основного API:

```text
GPS_CONSUMER_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
AUDIT_DATABASE_URL=postgresql+asyncpg://audit_user:...@audit-db:5432/audit_db
```

В тестовой среде live GPS consumer выключен, чтобы controller tests не требовали живую Kafka.

Базовый запуск:

```bash
docker compose up -d --build kafka kafka-init auto-parking nginx frontend
```

С уведомлениями и аудитом:

```bash
docker compose --profile notifications --profile audit up -d --build
```

С ботом:

```bash
docker compose --profile bot up -d --build
```

## Наблюдаемость И Нагрузочные Тесты

```text
monitoring/prometheus.yml    Prometheus scrape config
monitoring/grafana/          Grafana dashboards/provisioning
monitoring/goaccess/         GoAccess configs
logs/                        access/performance отчеты
load_tests/locustfile.py     Locust-сценарии
```

## Правила Для Новых Изменений

1. HTTP/WebSocket-слой держать тонким.
2. Бизнес-логику размещать в `service/`.
3. SQL, фильтрацию и relation loading держать в `repo/`.
4. Для межсервисных событий использовать `event_bus`.
5. Redis не использовать как брокер сообщений.
6. Микросервисы не должны импортировать `auto_parking.repo`, `auto_parking.service` и FastAPI-контроллеры монолита.
7. Агентские и IDE-служебные файлы не считать частью runtime-структуры проекта.
