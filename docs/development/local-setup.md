# Локальная разработка

Инструкция по запуску локального стенда.
Состав системы описан в [архитектуре](../architecture/project-structure.md), а
переменные окружения — в [конфигурации](../configuration.md).

## Требования

- Docker с плагином Compose;
- Git;
- Python 3.12 и Poetry — для запуска проверок вне контейнеров;
- Node.js и npm — только для Playwright E2E.

## Первый запуск

Создайте локальную конфигурацию и внешний volume основной БД:

```bash
cp .env.example .env
docker volume create auto-parking_db_data
```

Значения в `.env.example` предназначены только для локальной разработки. Перед
включением Telegram- или alert-профилей заполните соответствующие переменные.

Поднимите приложение и стек наблюдаемости:

```bash
docker compose up -d --build nginx prometheus grafana
```

Compose дождётся PostgreSQL, Redis и Kafka, создаст Kafka topics, применит
Alembic migrations, затем запустит API, frontend, Nginx, Prometheus, Tempo,
OpenTelemetry Collector и Grafana.

Проверьте состояние:

```bash
docker compose ps
curl -fsS http://localhost/api/health
```

## Локальные адреса

| Компонент | Адрес |
| --- | --- |
| Приложение | <http://localhost> |
| OpenAPI UI | <http://localhost/docs> |
| Метрики API | <http://localhost/metrics> |
| Prometheus | <http://localhost:9090> |
| Tempo API | <http://localhost:3200> |
| Grafana | <http://localhost:3000> |

Локальные учётные данные Grafana: `admin` / `admin`.

## Опциональные процессы

Telegram-бот и Kafka consumers включаются профилями:

```bash
docker compose \
  --profile bot \
  --profile notifications \
  --profile audit \
  up -d
```

Alertmanager и локальный SMTP inbox запускаются отдельно по инструкции
[Alerting](../monitoring/alerting.md). Генераторы демонстрационных данных
описаны в [операционных инструкциях](../operations/README.md).

## Повседневные команды

```bash
docker compose ps
docker compose logs --tail=100 auto-parking
docker compose up -d --build auto-parking frontend nginx
docker compose down
```

`docker compose down` сохраняет данные. Флаг `-v` удаляет именованные volumes
Redis, Kafka и observability-компонентов, но внешний `auto-parking_db_data`
нужно удалять отдельно и только если данные точно не нужны.

## Проверки кода

Все команды, матрица проверок, инфраструктура интеграционных тестов и
ограничения собраны в одном [руководстве по тестированию](../testing/README.md).

## Диагностика запуска

Если сервис не стал healthy, сначала смотрите его зависимости и последние логи:

```bash
docker compose ps
docker compose logs --tail=150 db kafka migrate auto-parking nginx
```

Типовые причины первого сбоя:

- отсутствует `.env`;
- не создан внешний volume `auto-parking_db_data`;
- занят порт `80`, `3000`, `9090`, `3200`, `4317` или `4318`;
- в `.env` не совпадают `POSTGRES_*` и `DATABASE_URL`;
- локальные volumes содержат данные от несовместимой старой конфигурации.
