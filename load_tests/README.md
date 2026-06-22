# Нагрузочное тестирование

В проекте используется Locust. Сценарии лежат в `load_tests/locustfile.py`.

## Запуск API

```bash
docker-compose up -d db redis auto-parking nginx
docker-compose exec -T auto-parking alembic upgrade head
```

Тесты бьют в nginx на `http://localhost`.

## Baseline health

Показывает верхнюю границу для легкого endpoint-а без БД и auth.

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

## Частые authenticated ручки

```bash
export LOCUST_TOKEN="$(poetry run python - <<'PY'
import httpx

response = httpx.post(
    "http://localhost/api/auth/login",
    json={"username": "superman", "password": "superman"},
    timeout=20,
)
response.raise_for_status()
print(response.json()["access_token"])
PY
)"

LOCUST_TOKEN="$LOCUST_TOKEN" \
LOCUST_VEHICLE_IDS=1,2,3,4,5 \
LOCUST_ENTERPRISE_IDS=2 \
poetry run locust \
  -f load_tests/locustfile.py HotApiUser \
  --host http://localhost \
  --headless \
  -u 50 \
  -r 10 \
  -t 60s \
  --csv logs/locust-hot-api
```

## Треки

Этот профиль тяжелее, потому что добавляет точки и поездки.

```bash
LOCUST_TOKEN="$LOCUST_TOKEN" \
LOCUST_VEHICLE_IDS=1,2,3,4,5 \
LOCUST_TRACK_DATE_FROM=2024-01-01T00:00:00+00:00 \
LOCUST_TRACK_DATE_TO=2026-01-01T00:00:00+00:00 \
poetry run locust \
  -f load_tests/locustfile.py TrackApiUser \
  --host http://localhost \
  --headless \
  -u 20 \
  -r 5 \
  -t 60s \
  --csv logs/locust-track-api
```

## Read/write профили

Read-only профиль дергает только `GET`-ручки. Write-only профиль делает цикл
`POST /api/vehicles` -> `PATCH /api/vehicles/{id}` -> `DELETE /api/vehicles/{id}`.

```bash
LOCUST_TOKEN="$LOCUST_TOKEN" \
poetry run locust \
  -f load_tests/locustfile.py ReadOnlyUser \
  --host http://localhost \
  --headless \
  -u 20 \
  -r 5 \
  -t 30s \
  --csv logs/locust-read-only
```

```bash
LOCUST_TOKEN="$LOCUST_TOKEN" \
LOCUST_WRITE_ENTERPRISE_ID=2 \
LOCUST_WRITE_MODEL_ID=1 \
poetry run locust \
  -f load_tests/locustfile.py WriteUser \
  --host http://localhost \
  --headless \
  -u 5 \
  -r 1 \
  -t 30s \
  --csv logs/locust-write-only
```

```bash
LOCUST_TOKEN="$LOCUST_TOKEN" \
LOCUST_WRITE_ENTERPRISE_ID=2 \
LOCUST_WRITE_MODEL_ID=1 \
poetry run locust \
  -f load_tests/locustfile.py ReadWriteUser \
  --host http://localhost \
  --headless \
  -u 20 \
  -r 5 \
  -t 30s \
  --csv logs/locust-read-write
```

## Что смотреть

- `Requests/s` - фактический RPS.
- `Failures/s` и failure count - ошибки под нагрузкой.
- `50%`, `95%`, `99%` - latency percentiles.
- Если RPS перестал расти при увеличении `-u`, значит уперлись в приложение, БД, nginx или машину.

## Текущие результаты

Локальные замеры через nginx, Docker Desktop, один `uvicorn` worker:

| Профиль | Users | RPS | Failures | p50 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `HealthUser` | `50` | `1733` | `0` | `24 ms` | `71 ms` |
| `HealthUser` | `100` | `1615` | `0` | `51 ms` | `110 ms` |
| `HotApiUser` | `5` | `80` | `0` | `48 ms` | `140 ms` |
| `HotApiUser` | `10` | `72` | `0` | `110 ms` | `320 ms` |
| `HotApiUser` | `20` | `77` | `0` | `240 ms` | `560 ms` |
| `TrackApiUser` | `3` | `54` | `0` | `42 ms` | `140 ms` |

Итог: health-only baseline держит около `1.6-1.7 kRPS`, а реальная смесь частых authenticated API - около `0.08 kRPS` при p95 около `140 ms`.

## Повтор с 5 workers

После добавления `--workers 5` в backend command:

| Профиль | Workers | Users | RPS | Failures | p50 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `HealthUser` | `1` | `100` | `1615` | `0` | `51 ms` | `110 ms` |
| `HealthUser` | `5` | `100` | `2149` | `0` | `45 ms` | `53 ms` |
| `HotApiUser` | `1` | `5` | `80` | `0` | `48 ms` | `140 ms` |
| `HotApiUser` | `5` | `5` | `96` | `0` | `46 ms` | `140 ms` |
| `HotApiUser` | `1` | `10` | `72` | `0` | `110 ms` | `320 ms` |
| `HotApiUser` | `5` | `10` | `144` | `0` | `50 ms` | `180 ms` |
| `HotApiUser` | `1` | `20` | `77` | `0` | `240 ms` | `560 ms` |
| `HotApiUser` | `5` | `20` | `190` | `0` | `79 ms` | `260 ms` |

Итог: 5 workers подняли реальную смесь API примерно до `0.19 kRPS`. Дальше надо отдельно проверять websocket/live-сценарии, потому что in-memory состояния существуют отдельно в каждом worker process.

## Read/write замер с 5 workers

| Профиль | Users | RPS | Failures | p50 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ReadOnlyUser` | `20` | `188` | `0` | `73 ms` | `260 ms` |
| `WriteUser` | `5` | `114` | `0` | `52 ms` | `61 ms` |
| `ReadWriteUser` | `20` | `155` | `0` | `86 ms` | `330 ms` |

`WriteUser` считает RPS по отдельным write-запросам. Один полный цикл записи состоит из трех запросов: `POST`, `PATCH`, `DELETE`. Поэтому `114 RPS` - это примерно `38` CRUD-циклов в секунду.
