# Анализ масштабируемости Auto Parking

## Потенциальные улучшения

1. `GET /api/vehicles`
   - Проверить, можно ли ускорить списочный ответ без изменения API-контракта.
   - Отдельно посмотреть загрузку `drivers`, добор timezone и сериализацию ответа.

2. Enterprise export
   - Поездки и GPS-точки уже переведены на batch-загрузку.
   - Следующий риск - большой размер итогового ответа, поэтому дальше надо выбирать между streaming response и background job.

3. Track endpoint-ы
   - Основная цена там не в мелких lookup-ах, а в размере ответа, сборке JSON/GeoJSON и cache hit rate.

4. Reports и PDF export
   - Тяжелую сборку отчетов/PDF лучше выносить из HTTP-запроса в background job или кешировать результат.

5. Индексы
   - Prefix-search по `vehicle_number` уже переведен на индексируемый `LIKE`.
   - Фильтр машин по `driver_id` уже получил обратный индекс на many-to-many таблице.
   - Частые default-ручки получили индексы под drivers, user-enterprise и notifications.
   - После повторных замеров проверить reports.

## Что уже сделано

Сделано 7 оптимизаций. Отдельно добавлены performance logs, но это не оптимизация, а способ нормально мерить результат.

### 1. Visibility-path для manager

Что было:

```python
user = await user_service.get_by_id(actor.id)
enterprise_ids = {e.id for e in user.enterprises}
```

Для каждого manager-запроса поднимался ORM-объект `User` и relation `user.enterprises`, хотя endpoint-ам нужны только `enterprise_id`.

Что изменено:

```python
stmt = (
    select(user_enterprise.c.enterprise_id)
    .select_from(User)
    .outerjoin(user_enterprise, User.id == user_enterprise.c.user_id)
    .where(User.id == user_id)
)
```

Теперь права manager читаются легким запросом напрямую из `user_enterprise`.

Что дало:

- `manager_lookup` после прогрева соединения, SQLAlchemy/asyncpg и буферов Postgres/OS: `24.4 ms -> 0.5 ms`.
- Это не прикладной кэш: для manager права каждый раз читаются из `user_enterprise`; admin вообще идет по short-circuit без запроса в БД.
- Warm handler `GET /api/vehicles` без FastAPI-сериализации: `4.9 ms -> 3.4 ms`.
- Warm полный запрос `GET /api/vehicles?limit=50&offset=0` внутри контейнера: около `6 ms`.

### 2. Enterprise export: batch-загрузка поездок

Что было:

```python
for vehicle in vehicles:
    trips = await trip_repo.get(TripFilter(vehicle_id=vehicle.id, ...))
```

Для `N` машин выполнялось `N` запросов за поездками.

Что изменено:

```python
trips = await trip_repo.get(
    TripFilter(vehicle_ids=vehicle_ids, started_from=date_from, ended_to=date_to)
)
```

Поездки всех машин предприятия за период грузятся одним запросом, затем группируются в памяти по `vehicle_id`.

Что дало:

- На текущих данных: `240` машин, `7223` поездки.
- Было: `240` запросов к `trip`, около `23.0 ms`.
- Стало: `1` batch-запрос, около `2.0 ms`.
- DB-часть поиска поездок стала примерно в `11 раз` быстрее.

### 3. `track-by-trips`: убран повторный lookup машины

Что было:

```python
vehicle = await vehicle_service.get_by_id(id)
...
await trip_track_service.get_grouped_track(vehicle_id=id, ...)
```

Контроллер грузил машину для visibility, а потом `TripTrackService` снова грузил ту же машину ради timezone.

Что изменено:

```python
await service.get_grouped_track(
    vehicle_id=id,
    ...,
    enterprise_timezone=timezone,
)
```

Контроллер передает timezone в сервис. Если сервис вызывают напрямую без timezone, старый fallback сохранен.

Что дало:

- Был лишний `vehicle by id` lookup на каждый успешный `track-by-trips` request.
- Старый лишний SQL-путь: около `2.5 ms`.
- Новый timezone lookup: около `0.8 ms`.
- Чистый выигрыш: около `1.7 ms` на request.

### 4. Enterprise export: batch-загрузка GPS-точек

Что было:

```python
for vehicle in vehicles:
    points = await track_repo.get(
        VehicleTrackFilter(vehicle_id=vehicle.id, intervals=intervals)
    )
```

После batch-загрузки поездок точки все еще грузились в цикле по машинам.

Что изменено:

```python
points = await track_repo.get(
    VehicleTrackFilter(
        vehicle_ids=vehicle_ids,
        trip_started_from=date_from,
        trip_ended_to=date_to,
    )
)
```

Точки всех машин предприятия за период грузятся одним запросом через join с `trip`, чтобы брать только точки, попадающие внутрь поездок. Потом они группируются в памяти по `vehicle_id`.

Что дало:

- На текущих данных: `240` машин, `7223` поездки, `721021` GPS-точка.
- DB-часть поиска точек: `1356 ms -> 1222 ms`, примерно `10%` быстрее.
- Главное практическое улучшение: вместо цикла до `240` SQL-запросов теперь `1` batch-запрос.
- На уровне приложения это снижает давление на пул соединений и убирает лишние DB round-trip-и.

### 5. Поиск машин по `vehicle_number_prefix`

Что было:

```python
Vehicle.vehicle_number.ilike(f"{prefix}%")
```

`ILIKE` делает case-insensitive поиск, но обычный btree-индекс под такой prefix-search нормально не используется. На текущей таблице это выглядело быстро только потому, что машин мало.

Что изменено:

```python
Vehicle.vehicle_number.like(f"{prefix.upper()}%")
```

Номера нормализуются в uppercase при создании и обновлении машины. В миграции существующие значения тоже приводятся к `upper(trim(vehicle_number))`.

Добавлен индекс:

```sql
CREATE INDEX ix_vehicle_vehicle_number_prefix
ON vehicle (vehicle_number text_pattern_ops);
```

Что дало:

- На текущих данных: `240` машин.
- Micro-benchmark на `1000` повторов поиска `А%`: `ILIKE` - `101.8 ms`, `LIKE` - `8.3 ms`.
- В пересчете на один поиск: `0.102 ms -> 0.008 ms`, примерно в `12 раз` быстрее, но абсолютный выигрыш пока маленький из-за размера таблицы.
- Новый индекс проверен: при `enable_seqscan=off` Postgres использует `Bitmap Index Scan on ix_vehicle_vehicle_number_prefix`.
- На синтетической таблице `500000` строк: `ILIKE` с `Seq Scan` - `171.5 ms`, `LIKE` с prefix-индексом - `13.9 ms`, тоже примерно в `12 раз` быстрее.
- Практический эффект проявится на росте таблицы: prefix-search получает индексируемый путь вместо обязательного просмотра всей `vehicle`.
- Побочный плюс: номера в БД теперь хранятся единообразно в uppercase.

### 6. Фильтр машин по `driver_id`

Что было:

```python
Vehicle.drivers.any(Driver.id == driver_id)
```

Фильтр использует many-to-many таблицу `vehicle_driver_assignment`. В ней уже был primary key:

```sql
PRIMARY KEY (vehicle_id, driver_id)
```

Такой индекс хорош для пути `vehicle -> drivers`, но для обратного поиска `driver -> vehicles` он не оптимален.

Что изменено:

```sql
CREATE INDEX ix_vehicle_driver_assignment_driver_vehicle
ON vehicle_driver_assignment (driver_id, vehicle_id);
```

Что дало:

- На текущих данных: `120` связей, поэтому Postgres все еще выбирает `Seq Scan`, потому что таблица маленькая.
- Новый индекс проверен: при `enable_seqscan=off` используется `Index Only Scan on ix_vehicle_driver_assignment_driver_vehicle`.
- На синтетической таблице `500000` связей: `34.7 ms -> 1.1 ms`, примерно в `30 раз` быстрее.
- Практический эффект проявится при росте числа назначений водителей: фильтр машин по водителю получает индексируемый путь.

### 7. Индексы для частых default endpoint-ов

Что было:

- `GET /api/drivers` фильтрует водителей по `enterprise_id`, но у `driver.enterprise_id` не было индекса.
- `GET /api/enterprises` и проверки видимости ходят по обратному направлению `enterprise -> users`, а `user_enterprise` был оптимальнее для направления `user -> enterprise`.
- `GET /api/notifications` и websocket unread-polling читают уведомления по `recipient_user_id` и сортируют по `created_at desc, id desc`.

Что изменено:

```sql
CREATE INDEX ix_driver_enterprise_id
ON driver (enterprise_id);

CREATE INDEX ix_user_enterprise_enterprise_user
ON user_enterprise (enterprise_id, user_id);

CREATE INDEX ix_notification_recipient_created_id
ON notification (recipient_user_id, created_at, id);

CREATE INDEX ix_notification_unread_recipient_created_id
ON notification (recipient_user_id, created_at, id)
WHERE read_at IS NULL;
```

Что дало:

- На текущей базе таблицы маленькие, поэтому Postgres часто выбирает `Seq Scan`, и это нормально.
- Synthetic `driver` на `500000` строк: `65.4 ms -> 13.5 ms` для фильтра по `enterprise_id`.
- Synthetic `user_enterprise` на `500000` строк: `28.8 ms -> 2.4 ms` для поиска managers/users предприятия.
- Synthetic unread notifications на `500000` строк: `12.8 ms -> 0.4 ms` для списка непрочитанных.
- Synthetic notification list на `500000` строк: ordered index дает `0.13 ms` для первых `50` уведомлений пользователя.

## Сводка эффекта

Грубая формула для оценки на высокой нагрузке:

```text
saved_seconds_per_second = saved_ms / 1000 * RPS
```

То есть `1 ms` экономии на запрос при `10 000 rps` дает примерно `10 секунд` суммарного ожидания меньше каждую секунду.

| Оптимизация | Экономия на 1 запрос | Эффект на `10 000 rps` |
| --- | ---: | ---: |
| Visibility-path | `~23.9 ms` на `manager_lookup` | `~239 секунд/сек` меньше ожидания |
| `GET /api/vehicles` handler | `~1.5 ms` | `~15 секунд/сек` меньше ожидания |
| `track-by-trips` | `~1.7 ms` | `~17 секунд/сек` меньше ожидания |
| Enterprise export trips | `~21 ms` на export | `~210 секунд/сек`, но `10 000 rps` export-ов - нереалистичный сценарий |
| Enterprise export GPS points | `~134 ms` на export DB-части | `~1340 секунд/сек`, но `10 000 rps` export-ов - нереалистичный сценарий |
| `vehicle_number_prefix` search | `~0.094 ms` на текущей таблице, `~157.6 ms` на synthetic `500k` | `~0.94 секунд/сек` на текущей таблице или `~1576 секунд/сек` на `500k`, но это только для запросов поиска по номеру |
| `driver_id` vehicle filter | текущая таблица слишком маленькая, `~33.6 ms` на synthetic `500k` | `~336 секунд/сек` на `10 000 rps` синтетической нагрузки по этому фильтру |
| `driver.enterprise_id` filter | текущая таблица слишком маленькая, `~51.9 ms` на synthetic `500k` | `~519 секунд/сек` на `10 000 rps` синтетической нагрузки по этому фильтру |
| `user_enterprise.enterprise_id` lookup | текущая таблица слишком маленькая, `~26.4 ms` на synthetic `500k` | `~264 секунд/сек` на `10 000 rps` синтетической нагрузки по этому lookup-у |
| notifications unread list | текущая таблица слишком маленькая, `~12.4 ms` на synthetic `500k` | `~124 секунд/сек` на `10 000 rps` synthetic unread-list нагрузки |

По DB round-trip-ам:

- `track-by-trips`: минус `1` лишний SQL lookup на request, то есть до `10 000` SQL-запросов/сек меньше при `10 000 rps`.
- Enterprise export: минус `239` SQL-запросов на один export на текущем наборе данных.
- Enterprise export GPS points: еще минус до `239` SQL-запросов на один full/guid export на текущем наборе данных.
- `vehicle_number_prefix`: вместо `ILIKE` без подходящего индекса теперь `LIKE` + `text_pattern_ops` индекс.
- `driver_id` filter: добавлен обратный индекс `(driver_id, vehicle_id)` для many-to-many таблицы.
- Default endpoint indexes: добавлены индексы для `driver.enterprise_id`, `user_enterprise(enterprise_id, user_id)` и notification list/unread.

## Что показали замеры

1. Visibility-path был реальным лишним ORM-путем и дал самый заметный выигрыш на маленьком endpoint-е.
2. Enterprise export имел классический N+1 по поездкам и точкам, поэтому batch снизил количество SQL round-trip-ов.
3. `track-by-trips` стал чище, но главный вес endpoint-а все равно в точках и сериализации ответа.
4. Обычные SQL-запросы машин и поездок сейчас быстрые на текущем объеме данных.
5. Поиск по `vehicle_number_prefix` подготовлен к росту таблицы через `LIKE` + prefix-индекс.
6. Фильтр машин по `driver_id` подготовлен к росту таблицы назначений через обратный индекс.
7. Default-ручки сейчас быстрые на маленькой базе, но без новых индексов начинали бы деградировать на росте `driver`, `user_enterprise` и `notification`.

## Нагрузочное тестирование

Добавлен Locust-сценарий: `load_tests/locustfile.py`.

Условия замеров:

- запуск локально через nginx: `http://localhost`;
- Docker Desktop, один `uvicorn` worker;
- включены middleware метрик, app access logs и uvicorn access logs;
- данные: `240` машин, `120` водителей, демо-треки по нескольким машинам;
- логин вынесен из нагрузки: перед тестом получается один bearer token, Locust мерит сами API-ручки.

Результаты:

| Профиль | Users | RPS | Failures | p50 | p95 | Вывод |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `HealthUser` | `50` | `1733` | `0` | `24 ms` | `71 ms` | Верхняя граница для легкого endpoint-а |
| `HealthUser` | `100` | `1615` | `0` | `51 ms` | `110 ms` | RPS не растет, latency растет |
| `HotApiUser` | `5` | `80` | `0` | `48 ms` | `140 ms` | Нормальная зона для частых authenticated ручек |
| `HotApiUser` | `10` | `72` | `0` | `110 ms` | `320 ms` | Уже плато, latency заметно хуже |
| `HotApiUser` | `20` | `77` | `0` | `240 ms` | `560 ms` | Throughput почти не растет |
| `TrackApiUser` | `3` | `54` | `0` | `42 ms` | `140 ms` | Треки тяжелее, но на малой конкуренции держатся |

Оценка в `kRPS`:

- health-only baseline: примерно `1.6-1.7 kRPS`;
- реальная смесь частых authenticated API: примерно `0.08 kRPS` при p95 около `140 ms`;
- если давить сильнее, полезный RPS почти не растет, вместо этого растет latency.

Главные наблюдения:

- обычный API-mix упирается не в количество Locust users, а в стоимость обработки запроса внутри одного backend worker;
- самые заметные endpoint-ы в mix: `GET /api/notifications`, `GET /api/drivers`, `GET /api/enterprises`, `GET /api/vehicles`;
- включенные access logs и performance logs заметно влияют на локальный benchmark;
- при агрессивном health-прогоне Docker Desktop перезапустил контейнеры, поэтому это не production-grade capacity test.

### Повторный замер с `--workers 5`

В `docker-compose.yaml` для backend добавлено:

```yaml
command: >
  uvicorn auto_parking.main:app
  --host 0.0.0.0
  --port 8000
  --workers 5
```

Фактический запуск проверен через `/proc/1/cmdline`, в логах поднялись `5` server process.

Результаты:

| Профиль | Workers | Users | RPS | Failures | p50 | p95 | Сравнение |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `HealthUser` | `1` | `100` | `1615` | `0` | `51 ms` | `110 ms` | baseline |
| `HealthUser` | `5` | `100` | `2149` | `0` | `45 ms` | `53 ms` | `+33%` RPS, p95 лучше |
| `HotApiUser` | `1` | `5` | `80` | `0` | `48 ms` | `140 ms` | baseline |
| `HotApiUser` | `5` | `5` | `96` | `0` | `46 ms` | `140 ms` | `+19%` RPS |
| `HotApiUser` | `1` | `10` | `72` | `0` | `110 ms` | `320 ms` | baseline |
| `HotApiUser` | `5` | `10` | `144` | `0` | `50 ms` | `180 ms` | примерно `x2` RPS |
| `HotApiUser` | `1` | `20` | `77` | `0` | `240 ms` | `560 ms` | baseline |
| `HotApiUser` | `5` | `20` | `190` | `0` | `79 ms` | `260 ms` | примерно `x2.5` RPS |

Вывод:

- Один worker действительно был существенным ограничением.
- Реальная смесь API выросла примерно с `0.08 kRPS` до `0.19 kRPS`.
- На `20` users latency уже заметная (`p95 260 ms`), но это сильно лучше старого `p95 560 ms`.
- Следующее узкое место уже не только worker count: тяжелее всего остаются `GET /api/notifications`, `GET /api/enterprises`, `GET /api/drivers` и сериализация/маппинг списков.
- WebSocket/live сценарии с несколькими workers нужно проверять отдельно, потому что in-memory publisher/hub живет отдельно в каждом worker process.

## Следующий план

1. Проверить live tracking и notifications websocket при `--workers 5`.
2. Для следующего честного benchmark-а отключить `uvicorn.access` и лишние access logs или вынести их в async/buffered logging.
3. Продолжить `GET /api/vehicles`: отдельно померить FastAPI-сериализацию и response model validation.
4. Для enterprise export решить вопрос с большим ответом: streaming response или background job.
5. Потом вернуться к reports после новых замеров.
