# Prometheus and Grafana

> Подробное руководство с теорией metrics, PromQL, добавлением custom metrics,
> Grafana-as-code и связью с OpenTelemetry находится в
> [`observability-guide.md`](observability-guide.md).

## What is wired together

The monitoring stack is part of `docker-compose.yaml`.

| Component | Compose service | Local URL | Purpose |
| --- | --- | --- | --- |
| API metrics endpoint | `auto-parking` | `http://localhost/metrics` | Exposes application metrics through Nginx. |
| Blackbox Exporter | `blackbox-exporter` | internal only | Probes the real `/api/health` route through Nginx. |
| Prometheus | `prometheus` | `http://localhost:9090` | Scrapes API, synthetic health, exporter, and self-metrics. |
| Grafana | `grafana` | `http://localhost:3000` | Shows the provisioned API dashboards. |

Inside the Docker network Prometheus scrapes the API directly:

```yaml
scrape_configs:
  - job_name: auto-parking-api
    metrics_path: /metrics
    static_configs:
      - targets:
          - auto-parking:8000
```

Grafana is provisioned with a Prometheus datasource:

```yaml
url: http://prometheus:9090
uid: prometheus
```

The default home dashboard path is:

```text
/var/lib/grafana/dashboards/auto-parking-api.json
```

That file is mounted from:

```text
monitoring/grafana/dashboards/auto-parking-api.json
```

Grafana also provisions two focused dashboards from the same directory:

| Dashboard | UID | What it shows |
| --- | --- | --- |
| Auto Parking Request Mix | `auto-parking-request-mix` | Request rate and volume split by route, method, and status code. |
| Auto Parking Response Time | `auto-parking-response-time` | Exact average latency plus p50, p95, and p99 by request type. |

Both focused dashboards exclude the synthetic `/api/health` probe so it does
not hide real API traffic.

## Application metrics

The FastAPI app registers metrics in `auto_parking/integrations/monitoring/prometheus.py`.

Current custom metrics:

| Metric | Type | Labels | Meaning |
| --- | --- | --- | --- |
| `auto_parking_http_requests_total` | counter | `method`, `path`, `status` | Total non-`/metrics` HTTP requests. |
| `auto_parking_http_request_duration_seconds` | histogram | `method`, `path` | Request duration distribution. |

The API runs with several Uvicorn workers in local compose. For that reason
`PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc` is set for the API container,
and the startup command clears and recreates that directory before Uvicorn starts.

## Synthetic health monitoring

Prometheus uses Blackbox Exporter to request the application through the same
Nginx route that local users access:

```text
Prometheus -> blackbox-exporter:9115 -> http://nginx/api/health
```

The probe runs every five seconds even when there is no user traffic. It exports:

| Metric | Meaning |
| --- | --- |
| `probe_success` | `1` when the route returns HTTP 200, otherwise `0`. |
| `probe_duration_seconds` | End-to-end health request duration. |
| `probe_http_status_code` | HTTP status returned by Nginx. |

The Grafana dashboard shows the current probe state, latency, and one-hour
availability. Synthetic `/api/health` requests are filtered out of the regular
request rate, latency, error-rate, and total-request panels.

## Run locally

```bash
docker compose up -d --build nginx prometheus grafana
```

This starts the dependency chain required by `nginx`, then starts Prometheus and
Grafana.

Open:

- application: `http://localhost`;
- Prometheus: `http://localhost:9090`;
- Grafana: `http://localhost:3000`;
- Grafana login: `admin` / `admin`.

To populate the API dashboards with a short read-only sample:

```bash
poetry run locust \
  -f load_tests/locustfile.py ReadOnlyUser \
  --host http://localhost \
  --headless \
  -u 1 \
  -r 1 \
  -t 15s \
  --only-summary \
  --exit-code-on-error 1
```

The scenario performs only authenticated `GET` requests. Even one user is
visible because the load-test client sends the next request without an
artificial wait.

## Verify

Check API metrics through Nginx:

```bash
curl -fsS http://localhost/metrics | head -50
```

Check API metrics from Prometheus container:

```bash
docker compose exec -T prometheus wget -qO- http://auto-parking:8000/metrics | head -50
```

Check Prometheus targets:

```bash
curl -fsS http://localhost:9090/api/v1/targets
```

Expected result: targets `auto-parking-api`, `auto-parking-health`,
`blackbox-exporter`, `otel-collector`, `tempo`, and `prometheus` have `health: up`.

Check that Prometheus receives API samples:

```bash
curl -fsS 'http://localhost:9090/api/v1/query?query=auto_parking_http_requests_total'
```

Check the synthetic HTTP probe:

```bash
curl -fsS --get \
  --data-urlencode 'query=probe_success{job="auto-parking-health"}' \
  http://localhost:9090/api/v1/query
```

Check Grafana datasource provisioning:

```bash
curl -fsS -u admin:admin http://localhost:3000/api/datasources/name/Prometheus
```

Check Grafana dashboard provisioning:

```bash
curl -fsS -u admin:admin http://localhost:3000/api/search?query=Auto%20Parking%20API
curl -fsS -u admin:admin \
  http://localhost:3000/api/dashboards/uid/auto-parking-request-mix
curl -fsS -u admin:admin \
  http://localhost:3000/api/dashboards/uid/auto-parking-response-time
```

## Troubleshooting

If Prometheus shows `auto-parking-api` as down, check that the API container is
running and that `/metrics` works inside the Docker network:

```bash
docker compose ps
docker compose logs --no-color --tail=120 auto-parking prometheus
docker compose exec -T prometheus wget -qO- http://auto-parking:8000/metrics
```

If `auto-parking-health` is down, inspect the exporter and probe the target
directly from its container:

```bash
docker compose logs --no-color --tail=120 blackbox-exporter prometheus nginx
docker compose exec -T blackbox-exporter wget -qO- \
  'http://localhost:9115/probe?module=auto_parking_health&target=http://nginx/api/health'
```

If Grafana opens but the dashboard is missing, check provisioning logs:

```bash
docker compose logs --no-color --tail=120 grafana
```

If metrics are empty after changing worker count, recreate the API container so
the multiprocess metrics directory is cleaned:

```bash
docker compose up -d --force-recreate auto-parking
```
