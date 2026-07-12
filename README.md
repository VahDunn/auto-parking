# Auto Parking

Auto Parking is a FastAPI-based fleet management project with PostgreSQL/PostGIS,
Redis, Kafka, a static frontend, Nginx, Prometheus, OpenTelemetry, Tempo, and Grafana.

## Quick start

Create `.env` from the project defaults used in your local environment, then run:

```bash
docker compose up -d --build nginx prometheus grafana
```

Main local endpoints:

| Service | URL |
| --- | --- |
| Application | http://localhost |
| API metrics | http://localhost/metrics |
| Prometheus | http://localhost:9090 |
| Tempo API | http://localhost:3200 |
| Grafana | http://localhost:3000 |

Grafana credentials for local compose are `admin` / `admin`.

## Documentation

Project documentation is collected under [`docs/`](docs/README.md):

- [`docs/monitoring/observability-guide.md`](docs/monitoring/observability-guide.md) - подробный гайд по всему observability stack с нуля.
- [`docs/monitoring/prometheus-grafana.md`](docs/monitoring/prometheus-grafana.md) - Prometheus and Grafana setup.
- [`docs/monitoring/opentelemetry-tempo.md`](docs/monitoring/opentelemetry-tempo.md) - OpenTelemetry and Tempo tracing.
- [`docs/monitoring/goaccess.md`](docs/monitoring/goaccess.md) - access log reports.
- [`docs/architecture/kafka.md`](docs/architecture/kafka.md) - Kafka event bus.
- [`docs/testing/e2e.md`](docs/testing/e2e.md) - Playwright E2E tests.
- [`docs/testing/load-testing.md`](docs/testing/load-testing.md) - Locust load tests.
- [`docs/operations/ci-cd.md`](docs/operations/ci-cd.md) - CI/CD flow.

## Monitoring

The API exposes Prometheus metrics at `/metrics`. In Docker Compose, Prometheus
scrapes `auto-parking:8000/metrics`, while Blackbox Exporter probes
`http://nginx/api/health` every five seconds. Grafana is provisioned with:

- a Prometheus datasource at `http://prometheus:9090`;
- a Tempo datasource at `http://tempo:3200`;
- the `Auto Parking API` dashboard from `monitoring/grafana/dashboards`;
- synthetic health state, latency, and one-hour availability panels.

See [`docs/monitoring/prometheus-grafana.md`](docs/monitoring/prometheus-grafana.md)
for metrics, and [`docs/monitoring/opentelemetry-tempo.md`](docs/monitoring/opentelemetry-tempo.md)
for tracing verification and troubleshooting.
