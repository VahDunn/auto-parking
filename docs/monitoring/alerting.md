# Alerting

Prometheus вычисляет правила из `monitoring/alerts.yml`; Alertmanager отвечает
только за группировку, подавление и доставку. Grafana показывает состояние
alerts, но не является источником правил.

```text
application metrics -> Prometheus rules -> Alertmanager -> Telegram + email
                                  \-> Grafana Auto Parking Alerts
```

## Запуск доставки

Rules загружаются Prometheus в базовом стеке. Для уведомлений задайте в `.env`:

```dotenv
TELEGRAM_BOT_TOKEN=<bot-token>
ALERT_TELEGRAM_CHAT_ID=<user-or-group-id>
```

Затем запустите профиль:

```bash
docker compose --profile alerts up -d alertmanager prometheus grafana
```

Mailpit поднимается как зависимость. Telegram и email получают одинаковые
firing/resolved notifications; письмо остаётся в локальном inbox
<http://localhost:8025> и не уходит в Интернет.

## Политика маршрутизации

- `critical`: отправляется круглосуточно, повтор каждые 30 минут;
- `warning`: заглушён с 23:00 до 08:00 `Europe/Moscow`, повтор каждые 6 часов;
- critical подавляет warning с теми же `service` и `alert_category`;
- alerts группируются по имени, сервису и диагностическим labels.

Источник политики — `monitoring/alertmanager.yml`.

## SQL errors

| Alert | Условие |
| --- | --- |
| `AutoParkingSQLFatalOrPanic` | хотя бы один `FATAL`/`PANIC` за 1 минуту |
| `AutoParkingSQLErrorBurst` | не менее 3 `ERROR` за 10 минут |
| `AutoParkingSQLWarningBurst` | не менее 10 `WARNING` за 10 минут |

API учитывает ошибки SQLAlchemy и сообщения PostgreSQL, увиденные соединениями
приложения. Это не замена централизованным логам PostgreSQL: ошибки других
клиентов в эти метрики не попадают.

## High latency

| Alert | Условие |
| --- | --- |
| `AutoParkingHTTPP95LatencyHigh` | HTTP p95 > 500 ms 5 минут при достаточном трафике |
| `AutoParkingHTTPP95LatencySpike` | HTTP p95 > 3× часового baseline и > 250 ms |
| `AutoParkingSQLP95LatencyHigh` | SQL p95 > 250 ms 5 минут при достаточном трафике |
| `AutoParkingSQLP95LatencySpike` | SQL p95 > 3× часового baseline и > 100 ms |

Baseline использует предыдущий час со смещением 5 минут. Точные PromQL
выражения, `for` и `keep_firing_for` всегда читаются в
`monitoring/alerts.yml` — таблица здесь объясняет назначение, а не дублирует
конфигурацию.

## HTTP errors

| Alert | Условие |
| --- | --- |
| `AutoParkingInterservice4xx` | любой внутренний 4xx за 5 минут |
| `AutoParkingInterservice5xx` | любой внутренний 5xx за 5 минут |
| `AutoParkingPublic4xxBurst` | не менее 20 внешних 4xx за 10 минут |
| `AutoParkingExternal5xxBurst` | не менее 3 внешних 5xx за 5 минут |

Внутренний caller определяется доверенным заголовком
`X-Auto-Parking-Service`; Nginx очищает одноимённый заголовок внешнего клиента.

## Расследование

1. Зафиксируйте `alertname`, время, timezone, severity и диагностические labels.
2. Проверьте rule в <http://localhost:9090/alerts> и группу в
   <http://localhost:9093>.
3. Откройте dashboard
   <http://localhost:3000/d/auto-parking-alerts/auto-parking-alerts>.
4. Сопоставьте окно времени с traces в Grafana Explore → Tempo.

Полезные запросы:

```promql
sum by (severity, operation, category) (
  increase(auto_parking_sql_events_total[10m])
)
```

```promql
sum by (caller, method, path, status) (
  increase(auto_parking_interservice_http_requests_total{status=~"4..|5.."}[10m])
)
```

```traceql
{ resource.service.name = "auto-parking-api" && status = error }
```

```traceql
{ span.db.system = "postgresql" && duration > 100ms }
```

Метрики не содержат exemplars/Trace ID, поэтому корреляция выполняется по
времени, route, status и duration.

## Безопасные сигналы для проверки

Команды не меняют бизнес-данные:

```bash
docker compose exec -T auto-parking \
  python -m auto_parking.minor_utilities.monitoring_smoke http-404 --count 3

docker compose exec -T auto-parking \
  python -m auto_parking.minor_utilities.monitoring_smoke sql-error --count 3

docker compose exec -T auto-parking \
  python -m auto_parking.minor_utilities.monitoring_smoke \
  sql-latency --count 3 --delay-seconds 0.3
```

Короткая серия latency отображается на dashboard, но может не выполнить
minimum traffic и `for` реального alert.

## Notification smoke

Проверить только доставку, не ожидая rule:

```bash
curl -fsS -X POST http://localhost:9093/api/v2/alerts \
  -H 'Content-Type: application/json' \
  -d '[{
    "labels": {
      "alertname": "AutoParkingNotificationSmoke",
      "severity": "critical",
      "service": "auto-parking-api",
      "alert_category": "smoke"
    },
    "annotations": {
      "summary": "Проверка monitoring-уведомлений",
      "description": "Synthetic alert для Telegram и email",
      "runbook": "docs/monitoring/alerting.md#notification-smoke"
    }
  }]'
```

После `group_wait` проверьте Telegram, Mailpit и счётчики:

```bash
curl -fsS http://localhost:9093/metrics \
  | grep 'alertmanager_notifications_.*integration="\(telegram\|email\)"'
```

## Валидация конфигурации

```bash
docker compose exec -T prometheus \
  promtool check config /etc/prometheus/prometheus.yml
docker compose exec -T prometheus \
  promtool check rules /etc/prometheus/alerts.yml
```

Команда для promtool rule tests и их место в матрице проверок находятся в
[руководстве по тестированию](../testing/README.md#prometheus-rule-tests). Они не
входят в текущий GitHub Actions CI. Исторические результаты последней проверки
зафиксированы в [отчёте по observability](../reports/observability.md).

## Production

Перед production замените Mailpit на реальный SMTP, вынесите secrets во внешний
secret manager, ограничьте доступ к UI, откалибруйте thresholds по SLO и
baseline, настройте HA/retention и регулярно проверяйте путь firing → delivery →
investigation → resolved.
