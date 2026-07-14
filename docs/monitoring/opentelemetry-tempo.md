# OpenTelemetry и Tempo

## Поток traces

```text
FastAPI -> OTLP/HTTP -> OpenTelemetry Collector -> OTLP/gRPC -> Tempo -> Grafana
```

| Компонент | Роль |
| --- | --- |
| `auto-parking` | создаёт server и dependency spans |
| `otel-collector` | принимает OTLP, ограничивает память, группирует и отправляет batches |
| `tempo` | хранит и индексирует локальные traces |
| `grafana` | ищет и показывает traces через datasource `tempo` |

Сейчас instrumented только основной API process. Подключены FastAPI,
SQLAlchemy, Redis, HTTPX и AIOKafka instrumentors. Notification- и audit-service
не отправляют traces в Collector.

`/metrics` и `/api/health` исключены. Root sampling применяется к входящему HTTP
или Kafka consumer; фоновые SQL/Redis/HTTPX/Kafka producer операции сами по себе
не создают поток разрозненных root traces.

Transactional outbox отделяет HTTP transaction от поздней публикации Kafka.
Без явного сохранения trace context в outbox payload сквозной parent-child trace
через эту границу не гарантируется.

## Конфигурация

| Переменная | Значение в локальном Compose | Назначение |
| --- | --- | --- |
| `OTEL_TRACING_ENABLED` | `true` | включает tracing API |
| `OTEL_SERVICE_NAME` | `auto-parking-api` | имя сервиса |
| `OTEL_SERVICE_VERSION` | `1.0.0` | версия resource |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | `http://otel-collector:4318/v1/traces` | OTLP/HTTP endpoint |
| `OTEL_TRACE_SAMPLE_RATIO` | `1.0` | доля новых entry-point traces |
| `OTEL_PYTHON_FASTAPI_EXCLUDED_URLS` | metrics/health regex | исключённые URL |

Код SDK находится в
`auto_parking/integrations/monitoring/tracing.py`, Collector — в
`monitoring/otel-collector.yml`, Tempo — в `monitoring/tempo.yml`.

## Поиск в Grafana

Откройте <http://localhost:3000/explore>, выберите datasource `Tempo` и режим
TraceQL.

Все traces API:

```traceql
{ resource.service.name = "auto-parking-api" }
```

Конкретный route:

```traceql
{ resource.service.name = "auto-parking-api" && span.http.route = "/api/vehicles" }
```

Ошибочные или медленные SQL spans:

```traceql
{ span.db.system = "postgresql" && status = error }
```

```traceql
{ span.db.system = "postgresql" && duration > 100ms }
```

## Проверка pipeline

```bash
docker compose ps auto-parking otel-collector tempo grafana
curl -fsS http://localhost:3200/ready
curl -fsS -u admin:admin http://localhost:3000/api/datasources/uid/tempo
```

Создать trace с предсказуемым ID и получить его из Tempo:

```bash
curl -fsS -o /dev/null \
  -H 'traceparent: 00-0123456789abcdef0123456789abcdef-0123456789abcdef-01' \
  http://localhost/openapi.json

curl -fsS \
  http://localhost:3200/api/traces/0123456789abcdef0123456789abcdef
```

Prometheus собирает внутренние метрики Collector и Tempo. Для pipeline особенно
полезны `otelcol_receiver_accepted_spans`, `otelcol_exporter_sent_spans` и
`otelcol_exporter_send_failed_spans`.

## Диагностика

```bash
docker compose logs --tail=120 auto-parking otel-collector tempo
docker compose exec -T prometheus \
  wget -qO- http://otel-collector:8888/metrics
```

Если accepted растёт, а sent нет, проверяйте exporter и доступность Tempo. Если
оба счётчика не растут, проверяйте endpoint приложения, sampling и excluded URL.
Недоступный Collector не должен останавливать HTTP API, но очередь exporter
ограничена и при долгом сбое traces могут быть потеряны.

Локальная конфигурация не включает TLS/auth, объектное хранилище, явный
retention или HA и не должна переноситься в production без доработки.
