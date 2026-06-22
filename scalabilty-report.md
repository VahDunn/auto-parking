# Анализ масштабируемости Auto Parking

Документ фиксирует, что уже проверено, какие узкие места найдены и что дало измеримый эффект. Замеры выполнялись локально в Docker Desktop через nginx, с 5 uvicorn workers, PostgreSQL и Redis в docker-compose.

## Потенциальные улучшения

1. `GET /api/vehicles`: уменьшать лишние SQL-запросы, аккуратно грузить `drivers`, не тащить relation-ы без необходимости.
2. Уведомления: текущий websocket-publisher хранит подключения в памяти процесса, поэтому для нескольких workers/сервисов нужен общий event bus.
3. Тяжелые отчеты и экспорт: большие выгрузки лучше переводить в streaming/background jobs или кешировать результат.
4. Track endpoint-ы: главный риск не один SQL-запрос, а размер ответа, сериализация JSON/GeoJSON и cache hit rate.
5. Логи и observability: access/performance logs полезны для анализа, но под нагрузкой сами становятся частью стоимости запроса.
6. Масштаб БД: часть индексов уже добавлена, дальше смотреть PgBouncer, read replicas и конкретные slow queries.

## Что сделано и что это дало

| Оптимизация | Было | Стало | Эффект |
| --- | --- | --- | --- |
| Visibility-path для manager | ORM `User` + `user.enterprises` | прямой запрос к `user_enterprise` | warm lookup `24.4 ms -> 0.5 ms` |
| Enterprise export trips | до 240 SQL-запросов по машинам | 1 batch-запрос | DB-часть `23.0 ms -> 2.0 ms` |
| Enterprise export GPS points | до 240 SQL-запросов по машинам | 1 batch-запрос | меньше round-trip-ов, DB-часть `1356 ms -> 1222 ms` |
| `track-by-trips` | повторный lookup машины ради timezone | timezone передается из контроллера | минус примерно `1.7 ms` на запрос |
| Поиск `vehicle_number_prefix` | `ILIKE`, плохо индексируется | normalized uppercase + `LIKE` + prefix index | текущие данные `101.8 ms -> 8.3 ms` на 1000 повторов |
| Фильтр машин по `driver_id` | индекс был только `(vehicle_id, driver_id)` | добавлен `(driver_id, vehicle_id)` | синтетика `34.7 ms -> 1.1 ms` |
| Частые default-ручки | не все lookup-и имели отдельный индекс | индексы под drivers, user-enterprise, notifications | меньше seq scan на росте данных |
| `GET /api/vehicles` | лишний timezone lookup | timezone берется из уже доступных данных | focused bench `214 rps -> 277 rps` |

## Нагрузочные замеры

| Сценарий Locust | Нагрузка | Результат |
| --- | --- | --- |
| `HealthUser` | 100 users, `/api/health` | около `2149 rps`, p50 `45 ms`, p95 `53 ms` |
| `HotApiUser` | 20 users, смесь частых ручек | около `190 rps`, p50 `79 ms`, p95 `260 ms` |
| `ReadOnlyUser` | 20 users, чтение | около `188 rps`, p50 `73 ms`, p95 `260 ms` |
| `WriteUser` | 5 users, CRUD | около `114 rps`, p50 `52 ms`, p95 `61 ms` |
| `ReadWriteUser` | 20 users, чтение + запись | около `155 rps`, p50 `86 ms`, p95 `330 ms` |
| `GET /api/vehicles` | focused bench | около `277 rps`, avg `70 ms`, p95 `159 ms` |

## Короткий вывод

Простой healthcheck локально держит примерно `2.1 kRPS`, но реальная смесь API сейчас ближе к `0.15-0.2 kRPS` на одном docker-инстансе с 5 workers. Это нормально для учебного проекта с активными логами, ORM, БД и сериализацией на критическом пути.

Чтобы идти к `10k rps`, одной правки кода мало: нужны горизонтальное масштабирование, общий event bus, контроль логирования, кэширование горячих чтений, pooler для БД, read replicas и вынос тяжелых операций из синхронного HTTP.
