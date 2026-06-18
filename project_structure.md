# Структура проекта Auto Parking

Этот документ описывает, где что лежит в проекте и какую роль выполняет каждый слой.

## Общая идея

Проект построен слоями:

```text
HTTP API -> API schemas -> services -> repositories -> DB models
                    \       /       \
                     domain models, domain enums, filters
                     ports -> integrations
```

Главное правило: зависимости должны идти сверху вниз. Нижние слои не должны знать про FastAPI, HTTP DTO и детали контроллеров. Внешняя инфраструктура подключается через `deps` и маленькие порты/protocols, а не протаскивается в домен или репозитории.

## Корень проекта

```text
auto_parking/
  api/
  bot/
  core/
  db/
  deps/
  filter/
  integrations/
  observability/
  ports/
  repo/
  service/
  main.py
frontend/
monitoring/
```

## `auto_parking/api`

HTTP-слой приложения.

### `auto_parking/api/router.py`

Главный API-router. Подключает v1-роутеры с публичными префиксами:

- `/vehicles`
- `/vehicle-models`
- `/drivers`
- `/enterprises`
- `/auth`
- `/reports`
- `/notifications`
- `/health`

### `auto_parking/api/v1`

Контроллеры FastAPI. Здесь живёт HTTP-логика:

- параметры query/path/body;
- `Depends`;
- `UploadFile`, `File`, `Query`;
- HTTP-статусы;
- `HTTPException`;
- преобразование доменных моделей в Pydantic-схемы ответа.

Контроллеры не должны напрямую ходить в базу и не должны содержать тяжёлую бизнес-логику.

Текущая структура:

```text
api/v1/
  auth.py
  drivers.py
  notifications.py
  vehicle_models.py
  enterprises/
    __init__.py
    common.py
    crud.py
    exports.py
    imports.py
  reports/
    __init__.py
    common.py
    crud.py
    exports.py
  vehicles/
    __init__.py
    common.py
    crud.py
    exports.py
    tracks.py
    trips.py
```

Пакеты `vehicles`, `enterprises`, `reports` устроены одинаково:

- `__init__.py` собирает router ресурса;
- `common.py` содержит общие HTTP-хелперы и маппинг доменных моделей в API-схемы;
- `crud.py` содержит базовые CRUD-эндпоинты;
- `exports.py` содержит эндпоинты экспорта;
- `imports.py`, `tracks.py`, `trips.py` содержат ресурсно-специфичные HTTP-операции.

### `auto_parking/api/schemas`

API DTO на Pydantic.

Здесь лежат входные и выходные модели публичного API:

- request-схемы;
- response-схемы;
- схемы сериализации;
- базовый `ApiSchema`.

Например, DTO авторизации (`LoginRequest`, `TokenResponse`) лежат в
`auto_parking/api/schemas/auth.py`, а не в контроллере.

Эти модели относятся к HTTP/API-слою. Их нельзя импортировать в репозитории. Сервисы тоже не должны возвращать API-схемы наружу: сервисы работают с доменными моделями.

## `auto_parking/service`

Сервисный слой приложения.

Здесь лежат use-case и orchestration-код:

- координация нескольких репозиториев;
- бизнес-проверки уровня сценария;
- импорт/экспорт;
- сборка отчётов;
- работа с треками и поездками;
- преобразование ORM-данных в доменные модели.

Сервисы должны возвращать доменные модели из `auto_parking/core/domain/models`, а не Pydantic-схемы API.
Для треков сервисы возвращают доменные track-модели (`VehicleTrackPointModel`,
`GeoJSONFeatureCollectionModel`, `TripTrackGroupModel`), а HTTP-слой преобразует их
в API-схемы и `Response` на границе контроллера.

Сервисы могут зависеть от:

- `repo`;
- `filter`;
- `core.domain.models`;
- `core.domain.enums`;
- маленьких ports/protocols из `auto_parking/ports` для внешней инфраструктуры;
- интеграций, если это уже выбранный локальный паттерн сценария.

Сервисы не должны зависеть от FastAPI и HTTP DTO.

В сервисах и доменной логике время хранится и обрабатывается только в UTC. Локализованное
время предприятия допустимо формировать только как выходное представление: в сервисном
mapper-е, на границе API или при экспорте. Оно не должно участвовать в бизнес-условиях
и расчетах.

Пример аккуратного порта: `CacheClient` в `auto_parking/ports/cache.py`. `BotService` знает только про контракт кэша, а не про Redis-клиент.
Другой пример: `ReverseGeocoder` в `auto_parking/ports/geocoding.py`; конкретный
Geoapify-адаптер остаётся в `auto_parking/integrations/geocoding`.

Кэш-клиент передаётся в `BotService` явно через `__init__`. Для одного-двух конкретных сценариев кэш лучше держать простыми прямыми обращениями к `self._cache`, без универсальных декораторов и скрытого прикрепления контекста в `deps`.

## `auto_parking/repo`

Репозиторный слой.

Здесь лежит вся работа с SQLAlchemy:

- SQL-запросы;
- фильтрация на уровне БД;
- загрузка связей;
- создание, обновление и удаление ORM-сущностей.

Репозитории работают с ORM-моделями из `auto_parking/db/models` и фильтрами из `auto_parking/filter`.

Для списочных чтений используется единый контракт `get(filter_obj)`. Различия между
сценариями поиска выражаются полями внутреннего фильтра, а не отдельными методами вида
`get_coordinates`, `get_by_intervals` или `get_for_export`. Репозиторий отвечает за SQL и
DB-представление данных; группировка точек по поездкам и построение JSON/GeoJSON остаются
в сервисном слое.

Репозитории не должны:

- импортировать FastAPI;
- импортировать API-схемы;
- выбрасывать HTTP-ошибки;
- знать про контроллеры.

## `auto_parking/db`

DB-слой.

### `auto_parking/db/models`

SQLAlchemy ORM-модели. Они описывают структуру таблиц и связи между ними.

DB-модели не являются API DTO и не являются доменными моделями. Они отражают схему хранения.

### Остальные файлы `db`

Инфраструктура базы:

- engine/session;
- события SQLAlchemy;
- admin-интеграция;
- базовая настройка моделей.

## `auto_parking/filter`

Внутренние фильтры приложения.

Фильтры используются сервисами и репозиториями для передачи параметров поиска:

- `DriverFilter`;
- `EnterpriseFilter`;
- `TripFilter`;
- `UserFilter`;
- `VehicleFilter`;
- `VehicleModelFilter`;
- базовый `BaseFilter`.

Фильтры являются внутренними объектами и не относятся к HTTP API. Поэтому они лежат отдельно от `api/schemas`.

Предпочтительный формат фильтров: простые dataclass-модели.

У `BaseFilter` есть флаг `load_relations=True`. Значение `False` используется
точечно, когда достаточно полей самой ORM-строки. Репозитории со связями явно
применяют `noload(...)`, чтобы отключить модельные `lazy="selectin"` загрузки.

## `auto_parking/core`

Чистое ядро и общие базовые элементы.

### `auto_parking/core/domain/models`

Доменные модели.

Они используются как внутренний формат данных между сервисами и контроллерами:

- `DomainModel`;
- `DriverModel`;
- `EnterpriseModel`;
- `VehicleModel`;
- `TripModel`;
- `ReportModel`;
- `NotificationModel`;
- модели треков и GeoJSON;

Доменные модели не должны зависеть от FastAPI, SQLAlchemy, репозиториев или HTTP.

### `auto_parking/core/domain/enums`

Доменные enum-значения:

- роли пользователей;
- типы уведомлений;
- форматы импорта/экспорта;
- типы и периоды отчётов;
- форматы треков.

Enum-ы можно использовать в API-схемах, сервисах, репозиториях и DB-моделях, если они действительно описывают доменное значение.

### `auto_parking/core/security`

Безопасность и авторизация:

- JWT;
- пароли;
- роли;
- actor-модель;
- bearer-auth;
- интеграция с admin-интерфейсом.

### `auto_parking/core/utils`

Небольшие общие утилиты, например работа с датой и временем.

### Прочие файлы `core`

- `config.py` — настройки приложения;
- `errors.py` — общие ошибки приложения;
- `handlers.py` — регистрация exception handlers;
- `logger.py` — настройка логирования.

## `auto_parking/deps`

Composition root и зависимости FastAPI.

Здесь собираются зависимости для контроллеров:

- сервисы;
- репозитории;
- интеграции;
- access-control;
- visibility-фильтры;
- общие зависимости.

`deps` может знать про FastAPI `Depends`, потому что это часть HTTP composition root. Бизнес-логика сюда не переносится.

### `auto_parking/deps/cache.py`

Собирает кэш-клиент для сервисов приложения:

- если задан `REDIS_URL`, создаёт Redis-адаптер;
- если Redis не настроен, возвращает `NullCacheClient`;
- скрывает детали `redis.asyncio` от `BotService`.

## `auto_parking/integrations`

Адаптеры внешних сервисов.

Сейчас здесь находятся:

```text
integrations/cache/
integrations/geocoding/
integrations/monitoring/
```

`integrations/monitoring` содержит Prometheus middleware и endpoint `/metrics`.

## `auto_parking/observability`

Общие helpers наблюдаемости, которые не являются адаптерами конкретной внешней
системы.

Сейчас здесь находится `performance.py`: он формирует JSONL-события
`http_request` и `cache_lookup` через стандартный Python `logging`.
В Docker ротируемые файлы сохраняются в локальный каталог `logs/`, который не
коммитится.

Интеграции должны быть подключаемыми через сервисы или `deps`, а не использоваться напрямую из репозиториев.

### `auto_parking/integrations/cache`

Redis-адаптер инфраструктурного кэша.

Правило: Redis не должен протекать в домен, репозитории и контроллеры. `BotService` зависит от `CacheClient`, а `RedisCacheClient` остаётся конкретной реализацией в `integrations`.

Сейчас кэшируются готовые сводки пробега Telegram-бота и несколько точечных backend-чтений: машина по ID, модель машины по имени и готовый payload ответа трека с учетом формата и timezone предприятия. Кэш машины обновляется или удаляется при mutation через `VehicleService`. Сводки и треки обновляются по TTL без сложных каскадных CRUD-инвалидаций. Redis ограничен `128mb` памяти и использует политику `allkeys-lru`, поэтому давно неиспользуемые ключи вытесняются автоматически.

### `auto_parking/integrations/geocoding`

Адаптер reverse geocoding. Он используется в сценариях, где нужно обогатить
координаты адресами. Сервисный слой зависит от нейтрального порта
`auto_parking/ports/geocoding.py`, а не от этого пакета напрямую.

### `auto_parking/integrations/monitoring`

Prometheus-инструментация FastAPI:

- middleware считает количество HTTP-запросов;
- middleware измеряет длительность HTTP-запросов;
- `/metrics` отдаёт данные в формате Prometheus.

Бизнес-сервисы не должны импортировать `prometheus_client`.

## `auto_parking/ports`

Нейтральные контракты внешних возможностей приложения.

Здесь лежат маленькие протоколы без инфраструктурных реализаций. Например, `CacheClient` описывает операции кэша, но не знает о Redis. Конкретные адаптеры остаются в `auto_parking/integrations`.
`ReverseGeocoder` описывает reverse geocoding без привязки к Geoapify или другой
конкретной внешней библиотеке.

## `monitoring`

Инфраструктурные конфиги мониторинга:

- `monitoring/prometheus.yml` — scrape-настройки Prometheus;
- `monitoring/grafana/provisioning/` — автоподключение Prometheus и dashboard-provider;
- `monitoring/grafana/dashboards/` — готовые dashboard JSON.

Prometheus доступен на `http://localhost:9090`, Grafana — на `http://localhost:3000`.

## `auto_parking/bot`

Telegram-бот как отдельный входной адаптер.

Здесь лежат:

- Telegram long polling client;
- обработчики команд и кнопок;
- состояние диалога;
- API client для обращения к backend;
- bot service для сценариев бота.

Бот не должен ходить в БД напрямую. Если ему нужны данные системы, он должен использовать HTTP API или явно подключённый сервисный слой, не обходя архитектуру.

## `frontend`

Статический frontend, который ходит в HTTP API.

Текущая структура разделяет:

- API-клиенты frontend;
- состояние приложения;
- UI-рендеринг;
- feature-модули.

Backend-изменения не должны ломать публичный API-контракт frontend без отдельного решения.

## `auto_parking/minor_utilities`

Вспомогательные утилиты проекта.

Перед добавлением нового кода сюда лучше проверить, не относится ли он к конкретному слою: `core/utils`, `service`, `repo` или `integrations`.

## Направление зависимостей

Разрешённое направление:

```text
api/v1 -> service -> repo -> db/models
api/v1 -> api/schemas
api/v1 -> core/domain/models
api/v1 -> filter
service -> core/domain/models
service -> core/domain/enums
service -> filter
service -> ports
repo -> filter
repo -> db/models
deps -> service/repo/integrations
integrations -> ports
integrations -> external systems
bot -> HTTP API / bot service
frontend -> HTTP API
```

Нежелательные зависимости:

```text
repo -> api/schemas
repo -> FastAPI
service -> api/schemas
service -> HTTPException
service -> redis.asyncio
core/domain/models -> SQLAlchemy
core/domain/models -> FastAPI
core/domain/enums -> FastAPI
db/models -> api/schemas
repo -> integrations
repo -> Redis
repo -> Telegram
```

## Где добавлять новый код

- Новый endpoint: `auto_parking/api/v1/<resource>/`.
- Новая request/response-схема: `auto_parking/api/schemas/`.
- Новый use-case: `auto_parking/service/`.
- Новый SQL-запрос или DB-операция: `auto_parking/repo/`.
- Новая ORM-модель: `auto_parking/db/models/`.
- Новый внутренний фильтр: `auto_parking/filter/`.
- Новая доменная модель: `auto_parking/core/domain/models/`.
- Новый enum: `auto_parking/core/domain/enums/`.
- Новая FastAPI-зависимость или wiring: `auto_parking/deps/`.
- Новый внешний адаптер: `auto_parking/integrations/`.
- Новый инфраструктурный порт для сервиса: `auto_parking/service/`, если он нужен именно сервисному сценарию.
- Новая реализация внешнего клиента: `auto_parking/integrations/`.
- Новая команда/диалог Telegram-бота: `auto_parking/bot/`.
- Новая frontend-фича: соответствующий подпакет `frontend/app/js/`.

## Короткие правила сопровождения

- Не переносить DB-доступ в контроллеры.
- Не возвращать API-схемы из сервисов.
- Не импортировать API-схемы в репозитории.
- Не класть HTTP-логику в сервисы и репозитории.
- Не менять DB-модели и миграции при чистой архитектурной уборке.
- Не плодить абстракции без необходимости.
- Не тащить Redis, Telegram или внешние API в домен и репозитории.
- Для инфраструктуры предпочитать маленький protocol/порт и адаптер в `integrations`.
- Предпочитать маленькие точечные изменения большим переписываниям.
