# OpenTelemetry and Tempo

> Полное введение со схемами, TraceQL, manual spans, Kafka propagation,
> sampling и конфигурацией находится в
> [`observability-guide.md`](observability-guide.md).

## Data flow

The local tracing path is:

```text
FastAPI -> OTLP/HTTP -> OpenTelemetry Collector -> OTLP/gRPC -> Tempo -> Grafana
```

| Component | Compose service | Local URL or port | Purpose |
| --- | --- | --- | --- |
| Instrumented API | `auto-parking` | internal `8000` | Creates request and dependency spans. |
| OpenTelemetry Collector | `otel-collector` | `4317` gRPC, `4318` HTTP | Receives, batches, and forwards traces. |
| Tempo | `tempo` | `http://localhost:3200` | Stores and queries traces. |
| Grafana | `grafana` | `http://localhost:3000` | Searches and displays traces through the `tempo` datasource. |

The API instruments:

- FastAPI server requests;
- SQLAlchemy database calls;
- Redis commands;
- outgoing HTTPX requests;
- AIOKafka producers and consumers.

`/metrics` and `/api/health` are excluded from tracing. The sampler starts new
traces only for inbound HTTP and Kafka consumer operations. SQL, Redis, HTTPX,
and Kafka producer spans are retained as children, but background polling does
not create a stream of disconnected root traces.

## Configuration

The main files are:

- `auto_parking/integrations/monitoring/tracing.py` - SDK and instrumentation setup;
- `monitoring/otel-collector.yml` - OTLP receiver, batching, and Tempo exporter;
- `monitoring/tempo.yml` - local single-binary Tempo storage;
- `monitoring/grafana/provisioning/datasources/tempo.yml` - Grafana datasource.

Environment variables:

| Variable | Local default | Meaning |
| --- | --- | --- |
| `OTEL_TRACING_ENABLED` | `true` in Compose | Enables API tracing. |
| `OTEL_SERVICE_NAME` | `auto-parking-api` | Tempo service name. |
| `OTEL_SERVICE_VERSION` | `1.0.0` | Resource service version. |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | `http://otel-collector:4318/v1/traces` | OTLP/HTTP trace endpoint. |
| `OTEL_TRACE_SAMPLE_RATIO` | `1.0` | Fraction of new entry-point traces to retain. |
| `OTEL_PYTHON_FASTAPI_EXCLUDED_URLS` | metrics and health regexes | Comma-separated URL exclusion patterns. |

Set `OTEL_TRACING_ENABLED=false` to run the API without tracing. For a
non-local deployment, lower the sampling ratio and configure authenticated TLS
between the application, Collector, and backend.

## Run and explore

```bash
docker compose up -d --build nginx prometheus tempo otel-collector grafana
```

Open Grafana, choose **Explore**, select the **Tempo** datasource, and use:

```traceql
{ resource.service.name = "auto-parking-api" }
```

To focus on one route:

```traceql
{ span.http.route = "/api/vehicles" }
```

## Verify

Check service health:

```bash
docker compose ps tempo otel-collector auto-parking grafana
curl -fsS http://localhost:3200/ready
docker compose exec -T prometheus wget -qO- http://otel-collector:13133/
```

Check Grafana provisioning:

```bash
curl -fsS -u admin:admin http://localhost:3000/api/datasources/uid/tempo
```

Generate a deterministic trace and retrieve it by ID:

```bash
curl -fsS -o /dev/null \
  -H "traceparent: 00-0123456789abcdef0123456789abcdef-0123456789abcdef-01" \
  http://localhost/openapi.json

curl -fsS \
  http://localhost:3200/api/traces/0123456789abcdef0123456789abcdef
```

Prometheus also scrapes the `otel-collector` and `tempo` jobs. Useful Collector
pipeline metrics include `otelcol_receiver_accepted_spans`,
`otelcol_exporter_sent_spans`, and `otelcol_exporter_send_failed_spans`.

## Troubleshooting

If traces do not arrive, inspect the complete path:

```bash
docker compose logs --no-color --tail=120 auto-parking otel-collector tempo
docker compose exec -T prometheus wget -qO- http://otel-collector:8888/metrics
```

An unavailable Collector does not prevent the API from serving requests. The
batch exporter retries transient delivery failures, while its queue and failure
metrics show whether spans are backing up or being dropped.
