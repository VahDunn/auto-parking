# Отчёт о внедрении observability

Дата исходной проверки: 11 июля 2026 года. Alerting дополнительно проверен
13 июля 2026 года. Это исторический снимок; текущая схема и runbook находятся в
[разделе monitoring](../monitoring/README.md).

## Реализованный контур

- Prometheus metrics FastAPI и SQL;
- synthetic health через Blackbox Exporter и Nginx;
- Grafana dashboards для API, request mix, latency и alerts;
- OpenTelemetry spans FastAPI, SQLAlchemy, Redis, HTTPX и AIOKafka;
- OTLP pipeline через Collector в Tempo;
- Prometheus recording/alert rules и доставка Alertmanager в Telegram/Mailpit.

Шумовые `/metrics` и `/api/health` traces исключены. Новый root trace создаётся
для входящего HTTP-запроса или Kafka consumer operation; dependency spans
сохраняются внутри такого trace.

## Зафиксированные проверки

В исходном прогоне были подтверждены валидность Compose и конфигураций
Collector, Tempo и Prometheus, provisioning Tempo datasource и Grafana
dashboards, readiness компонентов и сквозной путь Nginx → FastAPI → Collector →
Tempo → Grafana.

После контрольной нагрузки Collector принял и отправил по `5691` spans без
ошибок экспорта. Synthetic critical alert был доставлен в Telegram и SMTP inbox
Mailpit; delivery error counters остались нулевыми. Девять promtool scenarios
покрывали SQL severity, HTTP errors и p95 spikes.

Эти результаты не означают, что текущая рабочая копия автоматически прошла те
же проверки. Актуальные команды находятся в [Alerting](../monitoring/alerting.md),
[Prometheus и Grafana](../monitoring/prometheus-grafana.md) и
[OpenTelemetry и Tempo](../monitoring/opentelemetry-tempo.md).

## Контрольная read-only нагрузка

Один Locust user в течение 15 секунд выполнил 336 запросов без ошибок:

| Показатель | Результат |
| --- | ---: |
| Средняя интенсивность | 22,74 RPS |
| Среднее время ответа | 43 ms |
| `GET /api/vehicles` | 106 запросов, в среднем 15 ms |
| `GET /api/enterprises` | в среднем 77 ms |
| `GET /api/notifications` | в среднем 105 ms |

Одна из сохранённых на момент проверки трасс имела root span
`GET /api/vehicles`, длительность 10 ms и 5 spans. Trace ID из локального
retention намеренно не приводится как постоянная ссылка.

## Ограничения результата

- замер выполнен локально и не является production benchmark;
- локальный Tempo использует файловое хранилище без production HA;
- значения thresholds требуют калибровки на реальном baseline и SLO;
- production Compose не разворачивает этот monitoring stack.
