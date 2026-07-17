# Prometheus и Grafana

Документ описывает метрики, dashboards и диагностику. Запуск всего локального
стека находится в [локальной разработке](../development/local-setup.md), alerts
и доставка — в отдельном [alerting](alerting.md).

## Поток данных

```text
FastAPI /metrics --------------------> Prometheus -> Grafana
Nginx /api/health <- Blackbox Exporter -> Prometheus -> Grafana
Collector /metrics ------------------> Prometheus
Tempo /metrics ----------------------> Prometheus
```

Prometheus обращается к API по Docker DNS `auto-parking:8000`. Синтетическая проба
проходит через Nginx и тем самым проверяет не только процесс FastAPI, но и
пользовательский маршрут до `/api/health`.

## Метрики приложения

| Метрика | Тип | Labels | Назначение |
| --- | --- | --- | --- |
| `auto_parking_http_requests_total` | counter | `method`, `path`, `status` | HTTP-запросы, кроме `/metrics` |
| `auto_parking_http_request_duration_seconds` | histogram | `method`, `path` | latency HTTP |
| `auto_parking_http_error_responses_total` | counter | `audience`, `caller`, `error_type` | стабильный сигнал 4xx/5xx для rules |
| `auto_parking_interservice_http_requests_total` | counter | `caller`, `method`, `path`, `status` | внутренний HTTP-трафик |
| `auto_parking_sql_events_by_severity_total` | counter | `severity` | SQL-события для rules |
| `auto_parking_sql_events_total` | counter | `severity`, `operation`, `category` | детализация SQL errors/messages |
| `auto_parking_sql_query_duration_seconds` | histogram | `operation` | latency SQL |

HTTP пути нормализуются по шаблону FastAPI route, чтобы ID сущностей не
создавали лишнего. SQL statements и тексты ошибок не
помещаются в labels.

Локальный API работает с несколькими Uvicorn воркерами, поэтому включён режим
`PROMETHEUS_MULTIPROC_DIR`. Startup-команда очищает этот каталог перед запуском;
при ручном изменении workers контейнер нужно пересоздать.

## Health (синтетический)

Blackbox Exporter публикует:

- `probe_success` — `1`, если Nginx вернул ожидаемый HTTP статус;
- `probe_duration_seconds` — полная длительность проверки;
- `probe_http_status_code` — фактический статус.

Health-запросы исключены из пользовательских RPS/latency панелей и трейсов.

## Provisioned dashboards

| Dashboard | UID | Назначение |
| --- | --- | --- |
| Auto Parking API | `auto-parking-api` | общий health, RPS, errors и latency |
| Auto Parking Request Mix | `auto-parking-request-mix` | методы, routes и statuses |
| Auto Parking Response Time | `auto-parking-response-time` | average, p50, p95 и p99 |
| Auto Parking Alerts | `auto-parking-alerts` | firing alerts, SQL/HTTP signals и baseline |

JSON хранится в `monitoring/grafana/dashboards`, provisioning — в
`monitoring/grafana/provisioning`. Provision-дашборды следует менять в JSON;
изменение только через UI не является постоянным.

## Проверка

```bash
curl -fsS http://localhost/metrics | head -50
curl -fsS http://localhost:9090/-/ready
curl -fsS 'http://localhost:9090/api/v1/query?query=up'
curl -fsS -u admin:admin http://localhost:3000/api/datasources/uid/prometheus
curl -fsS -u admin:admin \
  http://localhost:3000/api/dashboards/uid/auto-parking-api
```

Проверка:

```bash
curl -fsS --get \
  --data-urlencode 'query=probe_success{job="auto-parking-health"}' \
  http://localhost:9090/api/v1/query
```

## Полезные PromQL-запросы

RPS по route:

```promql
sum by (method, path) (rate(auto_parking_http_requests_total[5m]))
```

HTTP p95:

```promql
histogram_quantile(
  0.95,
  sum by (le, method, path) (
    rate(auto_parking_http_request_duration_seconds_bucket[5m])
  )
)
```

Доля 5xx:

```promql
sum(rate(auto_parking_http_requests_total{status=~"5.."}[5m]))
/
sum(rate(auto_parking_http_requests_total[5m]))
```

## Диагностика

Если target down:

```bash
docker compose ps
docker compose logs --tail=120 auto-parking nginx blackbox-exporter prometheus
docker compose exec -T prometheus \
  wget -qO- http://auto-parking:8000/metrics
```

Если Grafana не видит dashboard или datasource:

```bash
docker compose logs --tail=120 grafana
```

Если series пропали после изменения числа workers:

```bash
docker compose up -d --force-recreate auto-parking
```

Пороговые условия не дублируются здесь: источником истины остаётся
`monitoring/alerts.yml`, а порядок расследования описан в [Alerting](alerting.md).
