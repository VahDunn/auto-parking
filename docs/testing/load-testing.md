# Нагрузочное тестирование

Locust-сценарии из `load_tests/locustfile.py` измеряют латентность, RPS и ошибки
работающего HTTP-стенда. Это ручные прогоны, а не функциональный
pass/fail кейс, не входят в GitHub Actions.

Общие Python-проверки
описаны в [обзоре тестирования](README.md).

## Безопасность

> Locust не проверяет hostname и не защищает production от запуска мутационных
> профилей. `WriteUser` и `ReadWriteUser` создают, изменяют и удаляют автомобили.
> Используйте отдельный стенд и отдельную БД.

Write-профили удаляют созданные записи после каждого успешного CRUD-цикла и
пытаются очистить оставшиеся записи при остановке user, так как 
аварийное завершение процесса или нештатный ответ API может оставить данные.

Перед прогоном проверьте target в `--host`, выбранные enterprise/model ID и
учётную запись. Для воспроизводимого замера не запускайте Locust одновременно с
E2E, seed или другими нагрузочными процессами.

## Подготовка стенда

Установить dev-зависимости и создать каталог для CSV:

```bash
poetry install --with dev --no-interaction
mkdir -p logs
```

Поднять локальное приложение за Nginx:

```bash
docker compose up -d --build nginx
curl -fsS http://localhost/api/health
```

Compose-сервис `migrate` применяет Alembic migrations как зависимость backend.
Authenticated-профилям нужны пользователь и подходящие тестовые данные:

- существующие vehicle IDs для detail/track запросов;
- существующие enterprise IDs для фильтров;
- существующие enterprise и vehicle model для write-профилей.

По умолчанию каждый виртуальный пользователь входит как `superman` / `superman`.
Можно передать другой login/password или готовый access token.

## Профили

| Класс | Нагрузка | Мутации |
| --- | --- | --- |
| `HealthUser` | непрерывный `GET /api/health`, без auth | нет |
| `HotApiUser` | взвешенная смесь частых list/detail GET-запросов | нет |
| `ReadOnlyUser` | alias `HotApiUser` с тем же набором задач | нет |
| `TrackApiUser` | задачи `HotApiUser` плюс track и trips GET-запросы | нет |
| `WriteUser` | цикл `POST` → `PATCH` → `DELETE` автомобиля | да |
| `ReadWriteUser` | задачи `HotApiUser` плюс CRUD-цикл с меньшим весом | да |

`TrackApiUser` не является изолированным бенчмарков: из-за наследования он
одновременно выполняет обычные hot API requests.

У всех профилей `wait_time = 0`, поэтому они создают максимально возможный плотный поток
запросов.

## Переменные окружения

| Переменная | Default | Использование |
| --- | --- | --- |
| `LOCUST_USERNAME` | `superman` | login при старте виртуального пользователя |
| `LOCUST_PASSWORD` | `superman` | password при login |
| `LOCUST_TOKEN` | не задан | готовый bearer token; если задан, login не выполняется |
| `LOCUST_VEHICLE_IDS` | `1,2,3,4,5` | detail, track и trips requests |
| `LOCUST_ENTERPRISE_IDS` | `2` | enterprise filter в read-профилях |
| `LOCUST_WRITE_ENTERPRISE_ID` | `2` | enterprise для создаваемых автомобилей |
| `LOCUST_WRITE_MODEL_ID` | `1` | vehicle model для создаваемых автомобилей |
| `LOCUST_TRACK_DATE_FROM` | `2024-01-01T00:00:00+00:00` | начало track interval |
| `LOCUST_TRACK_DATE_TO` | `2026-01-01T00:00:00+00:00` | конец track interval |


## Запуск

Общий шаблон:

```bash
poetry run locust \
  -f load_tests/locustfile.py PROFILE \
  --host http://localhost \
  --headless \
  -u USERS \
  -r SPAWN_RATE \
  -t DURATION \
  --csv logs/RESULT_PREFIX
```

Замените плейсхолдеры реальными значениями. Например, health
baseline без auth:

```bash
poetry run locust \
  -f load_tests/locustfile.py HealthUser \
  --host http://localhost \
  --headless \
  -u 50 \
  -r 10 \
  -t 30s \
  --csv logs/locust-health
```

С аутентификацией и явно выбранными данными:

```bash
LOCUST_VEHICLE_IDS=1,2,3,4,5 \
LOCUST_ENTERPRISE_IDS=2 \
poetry run locust \
  -f load_tests/locustfile.py HotApiUser \
  --host http://localhost \
  --headless \
  -u 20 \
  -r 5 \
  -t 60s \
  --csv logs/locust-hot-api
```

Профиль на отдельном стенде:

```bash
LOCUST_WRITE_ENTERPRISE_ID=2 \
LOCUST_WRITE_MODEL_ID=1 \
poetry run locust \
  -f load_tests/locustfile.py WriteUser \
  --host http://localhost \
  --headless \
  -u 5 \
  -r 1 \
  -t 30s \
  --csv logs/locust-write
```

Другие профили запускаются путем замены имени класса и подбора
нагрузки. Для `TrackApiUser` дополнительно задается корректный временной интервал.
для `ReadWriteUser` действуют одновременно переменные на запись и чтение.

## Как читать результат

- `Requests/s` — фактическая интенсивность завершённых запросов;
- failure count и `Failures/s` — ошибки API и проверки ответов в сценарии;
- p50, p95 и p99 — распределение латентности, а не среднее значение;
- plateau RPS при росте `-u` — признак насыщения приложения, БД, Nginx или хоста;
- write RPS считает отдельные HTTP запросы: один полный CRUD-цикл состоит из
  трёх запросов.
