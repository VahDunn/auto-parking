# Auto Parking

Auto Parking — сервис управления автопарком на FastAPI. Проект включает
REST/WebSocket API, статический веб-интерфейс, Telegram-бота, событийное
взаимодействие через Kafka, PostgreSQL/PostGIS, Redis и локальный стек
наблюдаемости.

## Возможности

- управление предприятиями, автомобилями, водителями, поездками и отчётами;
- импорт и экспорт данных, GPS-треки и live-обновления карты;
- ролевой доступ и Telegram-интерфейс;
- уведомления и аудит через отдельные Kafka consumers;
- метрики, трассировки, дашборды и operational alerts;
- unit, integration, E2E и нагрузочные тесты.

## С чего начать

Каноническая карта документации находится в
[`docs/README.md`](docs/README.md).

- Локальный запуск: [`docs/development/local-setup.md`](docs/development/local-setup.md)
- Архитектура: [`docs/architecture/project-structure.md`](docs/architecture/project-structure.md)
- Конфигурация: [`docs/configuration.md`](docs/configuration.md)
- Тестирование: [`docs/testing/README.md`](docs/testing/README.md)
- CI: [`docs/ci-cd.md`](docs/ci-cd.md)
- Деплой и откат: [`docs/deployment.md`](docs/deployment.md)

После запуска API публикует интерактивную OpenAPI-документацию на `/docs`.
Адреса локальных сервисов, команды запуска и проверок намеренно собраны в
руководстве по локальной разработке, чтобы README не становился второй копией
эксплуатационной документации.

## Основные технологии

Python 3.12, FastAPI, SQLAlchemy, PostgreSQL/PostGIS, Redis, Kafka, Docker
Compose, Alembic, Prometheus, OpenTelemetry, Tempo, Grafana, Pytest, Playwright
и Locust.

Проектная топология и её текущие ограничения описаны в
[`docs/architecture/project-structure.md`](docs/architecture/project-structure.md).
