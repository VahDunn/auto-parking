# Исторический отчёт о масштабируемости

Этот документ сохраняет ранее полученные локальные результаты. Это не актуальный
SLA, performance gate или инструкция по запуску. Методика текущих прогонов
описана в [руководстве по Locust](../testing/load-testing.md).

## Контекст и ограничения

Замеры выполнялись локально через Nginx в Docker Desktop с PostgreSQL и Redis из
Compose. Сравнивались один и пять Uvicorn workers. Для всех строк ниже failures
были равны нулю, если не указано обратное.

В исходных записях не зафиксированы commit, дата, характеристики host, лимиты
Docker и точный dataset. Поэтому цифры пригодны для исторического сравнения
изменений внутри того эксперимента, но не для сравнения с другим окружением и не
как гарантия production capacity.

## Один Uvicorn worker

| Профиль | Users | RPS | p50 | p95 |
| --- | ---: | ---: | ---: | ---: |
| `HealthUser` | 50 | 1733 | 24 ms | 71 ms |
| `HealthUser` | 100 | 1615 | 51 ms | 110 ms |
| `HotApiUser` | 5 | 80 | 48 ms | 140 ms |
| `HotApiUser` | 10 | 72 | 110 ms | 320 ms |
| `HotApiUser` | 20 | 77 | 240 ms | 560 ms |
| `TrackApiUser` | 3 | 54 | 42 ms | 140 ms |

Health endpoint достигал примерно `1.6–1.7 kRPS`. Смесь authenticated API
насыщалась около `0.08 kRPS`, а при росте users увеличивалась latency без
сопоставимого роста throughput.

## Пять Uvicorn workers

| Профиль | Users | RPS | p50 | p95 |
| --- | ---: | ---: | ---: | ---: |
| `HealthUser` | 100 | 2149 | 45 ms | 53 ms |
| `HotApiUser` | 5 | 96 | 46 ms | 140 ms |
| `HotApiUser` | 10 | 144 | 50 ms | 180 ms |
| `HotApiUser` | 20 | 190 | 79 ms | 260 ms |

На 20 users переход с одного worker на пять увеличил throughput `HotApiUser` с
77 до 190 RPS и снизил p95 с 560 до 260 ms. Для health endpoint рост был с 1615
до 2149 RPS при 100 users.

## Read/write-профили с пятью workers

| Профиль | Users | RPS | p50 | p95 |
| --- | ---: | ---: | ---: | ---: |
| `ReadOnlyUser` | 20 | 188 | 73 ms | 260 ms |
| `WriteUser` | 5 | 114 | 52 ms | 61 ms |
| `ReadWriteUser` | 20 | 155 | 86 ms | 330 ms |

`WriteUser` считает каждый HTTP request отдельно. Так как один CRUD-цикл состоит
из `POST`, `PATCH` и `DELETE`, 114 RPS соответствовали примерно 38 завершённым
циклам в секунду.

## Focused `GET /api/vehicles`

После исключения лишнего timezone lookup зафиксирован рост focused benchmark с
214 до 277 RPS. Для результата 277 RPS были записаны average latency 70 ms и p95
159 ms.

## Зафиксированный эффект отдельных оптимизаций

Эти microbenchmarks и DB-замеры выполнялись в том же цикле оптимизации, но не
являются строками Locust-таблиц.

| Изменение | До | После | Наблюдение |
| --- | ---: | ---: | --- |
| Visibility lookup для manager через `user_enterprise` | 24.4 ms | 0.5 ms | прямой запрос вместо загрузки ORM relation |
| Batch-загрузка trips для enterprise export | 23.0 ms | 2.0 ms | до 240 запросов заменены одним batch query |
| Batch-загрузка GPS points для enterprise export | 1356 ms | 1222 ms | сокращено число round trips, но обработка данных осталась дорогой |
| Нормализованный prefix search номера | 101.8 ms | 8.3 ms | 1000 повторов, `LIKE` и prefix index вместо `ILIKE` |
| Reverse index для фильтра по `driver_id` | 34.7 ms | 1.1 ms | синтетический запрос после индекса `(driver_id, vehicle_id)` |
| Передача известной timezone в `track-by-trips` | повторный lookup | lookup исключён | примерно −1.7 ms на запрос |

## Исторический вывод

В этом окружении пять workers заметно улучшили насыщенную authenticated смесь,
но реальный API оставался на уровне примерно `0.15–0.2 kRPS`, существенно ниже
health-only baseline. Наиболее заметный эффект дали устранение повторных lookup,
batch queries и индексы под фактические фильтры.

Эти данные не подтверждают достижимость `10 kRPS` текущим single-host stack.
Новые выводы следует делать только по повторному прогону с зафиксированными
commit, dataset, ресурсами, workers и полным набором параметров Locust.
