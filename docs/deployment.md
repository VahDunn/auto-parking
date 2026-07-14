# Production deployment

Production разворачивается на одном сервере через Docker Compose. GitHub Actions
копирует на сервер Compose-файл и Nginx config, скачивает заранее собранные images из
GHCR, применяет миграции и запускает stack.

Это single-server deployment без оркестратора и автоматического failover.

## Источники конфигурации

| Файл | Назначение |
| --- | --- |
| `.github/workflows/deploy.yml` | фактическая последовательность deployment |
| `deploy/docker-compose.prod.yaml` | production services, profiles, volumes и env |
| `deploy/.env.prod.example` | шаблон серверного `.env` |
| `nginx/nginx.conf` | внешний HTTP reverse proxy |
| `docs/ci-cd.md` | CI, images, inputs и GitHub secrets |

При расхождении документа с workflow или Compose источником истины являются YAML-файлы.

## Production topology

Services без profile запускаются всегда:

| Service | Назначение | Persistence/порт |
| --- | --- | --- |
| `db` | основная PostgreSQL/PostGIS | volume `db_data` |
| `audit-db` | отдельная PostgreSQL для аудита | volume `audit_db_data` |
| `redis` | cache и Telegram login registry | volume `redis_data` |
| `kafka` | single-node Kafka в KRaft mode | volume `kafka_data` |
| `kafka-init` | создание и обновление Kafka topics | одноразовый процесс |
| `auto-parking` | FastAPI/Uvicorn API | internal `8000`, host logs |
| `frontend` | статический frontend | internal `80` |
| `nginx` | единая HTTP-точка входа | `${HTTP_PORT:-80}:80` |

Дополнительные процессы включаются profiles:

| Profile | Service | Назначение |
| --- | --- | --- |
| `bot` | `telegram-bot` | Telegram long polling bot |
| `notifications` | `notification-service` | Kafka consumer и Telegram sender |
| `audit` | `audit-service` | Kafka consumer и запись audit events |
| `migrate` | `migrate` | `alembic upgrade head` |

Deploy workflow всегда включает `bot`, `notifications` и `audit`. Profile `migrate`
используется только для отдельного one-off запуска миграций.

Production Compose не содержит локальный observability stack: Prometheus, Blackbox
Exporter, Alertmanager, Mailpit, Tempo, OpenTelemetry Collector и Grafana не
разворачиваются. В production template нет `OTEL_TRACING_ENABLED`, поэтому tracing
основного API по умолчанию выключен.

Nginx принимает обычный HTTP. TLS termination, домен и сертификаты текущим stack не
настраиваются.

## Подготовка сервера

На сервере нужны:

- Docker Engine;
- Docker Compose v2 (`docker compose`);
- `curl`;
- SSH-пользователь с доступом к Docker;
- достаточно места для images и persistent volumes.

Пример начальной подготовки каталога:

```bash
sudo mkdir -p /opt/auto-parking/logs
sudo chown -R deploy:deploy /opt/auto-parking
```

Пользователь в группе `docker` фактически получает привилегированный доступ к
серверу. Используйте отдельный ключ и ограничивайте доступ к этому аккаунту.

### Серверный `.env`

Workflow не создаёт и не обновляет runtime `.env`. До первого deployment файл должен
существовать в выбранном `deploy_path`, по умолчанию:

```text
/opt/auto-parking/.env
```

Шаблон находится в `deploy/.env.prod.example`. Например, передайте его с локальной
машины и затем заполните на сервере:

```bash
scp deploy/.env.prod.example deploy@<server>:/opt/auto-parking/.env
ssh deploy@<server>
chmod 600 /opt/auto-parking/.env
```

Замените все `change-me`. Как минимум проверьте:

| Группа | Переменные |
| --- | --- |
| Images | `IMAGE_REGISTRY`, `IMAGE_NAMESPACE`, `IMAGE_TAG` |
| Основная БД | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL` |
| Audit DB | `AUDIT_POSTGRES_DB`, `AUDIT_POSTGRES_USER`, `AUDIT_POSTGRES_PASSWORD` |
| Security | `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TTL_MINUTES` |
| Runtime | `APP_ENV=prod`, `DEBUG=false`, `LOG_LEVEL`, `WEB_CONCURRENCY` |
| Integrations | `REDIS_URL`, Kafka consumer groups, `TELEGRAM_BOT_TOKEN` |
| Network | `HTTP_PORT` |

Пароль внутри `DATABASE_URL` должен совпадать с `POSTGRES_PASSWORD`. Значение
`IMAGE_NAMESPACE` имеет вид `<github-owner>/auto-parking`, без `ghcr.io/` и без
суффикса `/app`.

## Приоритет image-настроек

Во время автоматического deployment workflow перед каждой изменяющей stack командой
задаёт inline environment:

```text
IMAGE_REGISTRY=ghcr.io
IMAGE_NAMESPACE=<IMAGE_NAMESPACE secret или github-owner/auto-parking>
IMAGE_TAG=<workflow input image_tag>
```

Эти значения имеют приоритет над одноимёнными значениями серверного `.env` для
`pull`, `kafka-init`, `migrate` и `up`.

Следствия:

- `IMAGE_NAMESPACE` в server `.env` не выбирает images автоматического deployment;
- `IMAGE_TAG` в server `.env` не переопределяет input workflow;
- `IMAGE_REGISTRY` в server `.env` не меняет hardcoded `ghcr.io`;
- server `.env` всё равно должен содержать корректный namespace для последующего
  `docker compose ps` и ручных команд, которые workflow запускает без inline image env.

Все application secrets и runtime-параметры по-прежнему читаются из server `.env`.
Compose также поддерживает `${APP_ENV_FILE:-.env}`, но workflow не задаёт отдельный
`APP_ENV_FILE`, поэтому штатный путь — `.env` рядом с Compose-файлом.

## GitHub configuration

Список обязательных и опциональных repository secrets приведён в
[`ci-cd.md`](ci-cd.md#github-secrets).

У workflow два input:

- `image_tag`: `latest` или полный commit SHA;
- `deploy_path`: каталог stack на сервере.

Для предсказуемого результата используйте SHA успешного `CI`, а не `latest`.

## Первый deployment

1. Выполните успешный push в `main` и убедитесь, что все четыре images с нужным SHA
   появились в GHCR.
2. Подготовьте серверный каталог и `.env`.
3. Создайте GitHub secrets из `ci-cd.md`.
4. Откройте `Actions -> Deploy -> Run workflow`.
5. Укажите `image_tag` и `deploy_path`.

Workflow выполняет следующую последовательность:

1. Checkout репозитория и вычисление default image namespace.
2. Создание временного SSH key и добавление результата `ssh-keyscan` в
   `known_hosts`.
3. Создание `${deploy_path}` и `${deploy_path}/logs` на сервере.
4. Копирование:
   - `deploy/docker-compose.prod.yaml` в `${deploy_path}/docker-compose.yaml`;
   - `nginx/nginx.conf` в `${deploy_path}/nginx.conf`.
5. `docker login ghcr.io` с `GHCR_USERNAME` и `GHCR_TOKEN`.
6. Pull base services и profiles `bot`, `notifications`, `audit`.
7. Явный one-off запуск `docker compose run --rm kafka-init`.
8. One-off запуск `docker compose --profile migrate run --rm migrate`.
9. `docker compose --profile bot --profile notifications --profile audit up -d`.
10. `docker compose ps`.
11. Один запрос `curl -fsS http://localhost/api/health`.

Deployment считается успешным только если все команды, включая финальный health
request, завершились с кодом `0`.

### Повторный `kafka-init`

`kafka-init` не имеет profile. Workflow сначала запускает его явно как one-off, а
затем `docker compose ... up -d` создаёт штатный `kafka-init` ещё раз, потому что от
него зависит API. Текущая реализация init идемпотентна: она создаёт отсутствующие
topics и может увеличить число partitions, но не уменьшает их.

Это фактическое поведение текущего workflow, а не два разных этапа инициализации.

### Health check и `HTTP_PORT`

Compose публикует Nginx через `${HTTP_PORT:-80}`, но workflow всегда проверяет
`http://localhost/api/health`, то есть порт `80`.

Для штатного workflow оставляйте `HTTP_PORT=80`. При другом порте containers могут
успешно запуститься, но финальный шаг завершит deployment ошибкой.

Кроме того, API и Nginx не имеют Compose healthcheck. `up -d` ждёт запуска containers,
но не полной готовности API, а `curl` выполняется один раз без retry. Медленный старт
может дать ложное падение deployment.

## Проверка после deployment

На сервере:

```bash
cd /opt/auto-parking
docker compose --profile bot --profile notifications --profile audit ps
curl -fsS http://localhost/api/health
```

Основные логи:

```bash
docker compose logs --tail=100 auto-parking nginx
docker compose logs --tail=100 telegram-bot notification-service audit-service
docker compose logs --tail=100 kafka kafka-init
```

Проверка topics:

```bash
docker compose exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --list
```

## Ручное обновление

Штатный путь — workflow `Deploy`. Если требуется повторить его вручную на сервере,
явно задайте те же image values:

```bash
cd /opt/auto-parking
export IMAGE_REGISTRY=ghcr.io
export IMAGE_NAMESPACE=<github-owner>/auto-parking
export IMAGE_TAG=<commit-sha>

docker compose --profile bot --profile notifications --profile audit pull
docker compose run --rm kafka-init
docker compose --profile migrate run --rm migrate
docker compose --profile bot --profile notifications --profile audit up -d
curl -fsS http://localhost/api/health
```

Не запускайте обычный `up -d` как замену deployment: production API не зависит от
service `migrate`, поэтому такая команда сама по себе не применяет Alembic migrations.

## Rollback

Автоматического rollback нет. Для возврата application images можно повторно запустить
workflow `Deploy` и указать предыдущий рабочий SHA.

Такой rollback безопасен только при совместимой схеме БД. Workflow всегда выполняет
`alembic upgrade head` из выбранного image и никогда не выполняет `alembic downgrade`:

- уже применённые миграции не откатываются;
- старый image может не знать revision, записанный более новым deployment, и migration
  step завершится ошибкой;
- несовместимое изменение schema может сделать старый код неработоспособным даже при
  успешном запуске containers.

Перед изменениями schema нужны backup и план восстановления. Используйте
backward-compatible expand/contract migrations. Restore или Alembic downgrade должны
быть отдельной проверенной операцией, а не частью обычного image rollback.

## Troubleshooting

### Workflow падает на `ssh-keyscan`

Проверьте `DEPLOY_HOST`, DNS и доступность SSH на порту `22`. Текущий `ssh-keyscan`
не использует `DEPLOY_PORT`; сервер только с нестандартным SSH-портом этим workflow
полностью не поддержан без изменения шага настройки SSH.

Workflow доверяет ключу, который вернул `ssh-keyscan` во время запуска, и не сверяет
его с заранее сохранённым fingerprint.

### `ssh` или `scp` не подключается

Проверьте `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_PORT`, `authorized_keys`, права на
`deploy_path` и доступ пользователя к Docker socket.

### `docker login` или `pull` падает

Проверьте:

- `GHCR_USERNAME` и срок действия `GHCR_TOKEN`;
- право `read:packages` и visibility package;
- `IMAGE_NAMESPACE` secret;
- наличие всех четырёх images с выбранным тегом.

`docker login` сохраняет credentials в Docker config пользователя на сервере. Их
нужно отдельно ротировать или удалить при отзыве deploy-доступа.

### Compose не читает конфигурацию

Убедитесь, что рядом с `docker-compose.yaml` существуют `.env`, `nginx.conf` и каталог
`logs`. Без вывода значений secrets синтаксис можно проверить так:

```bash
cd /opt/auto-parking
docker compose config -q
```

Если изменились пароли БД после создания persistent volume, изменение `.env` не
переинициализирует существующую PostgreSQL автоматически.

### Миграции падают

Смотрите полный output шага `migrate` в GitHub Actions. One-off container запускается
с `--rm`, поэтому после завершения его logs могут не сохраниться как обычный Compose
service container.

Для диагностики проверьте `DATABASE_URL`, доступность `db` и совместимость Alembic
revision с выбранным image. Не запускайте downgrade без backup и отдельного плана.

### Containers запущены, а workflow красный

Проверьте `HTTP_PORT`. Финальный request всегда идёт на port `80`. Также возможна гонка
готовности API, потому что request выполняется сразу и без retry:

```bash
docker compose ps
docker compose logs --tail=100 auto-parking nginx
curl -v http://localhost/api/health
```

### Telegram services не работают

Проверьте `TELEGRAM_BOT_TOKEN`, `REDIS_URL`, Kafka bootstrap servers и consumer groups,
затем логи `telegram-bot` и `notification-service`. Workflow включает оба profile при
каждом deployment.

## Текущие эксплуатационные ограничения

- один сервер и один экземпляр каждого stateful service;
- Kafka без TLS/SASL и с replication factor `1`;
- PostgreSQL, Redis и Kafka работают в том же Compose stack, что и приложение;
- нет автоматических backup/restore и проверки backup перед миграциями;
- нет zero-downtime/blue-green/canary deployment;
- нет автоматического rollback при ошибке после миграции или частичном `up`;
- нет production monitoring, tracing и alerting stack;
- нет TLS termination в поставляемом Nginx config;
- нет resource limits и healthchecks для application services;
- нет очистки старых images и контроля заполнения диска;
- нет `concurrency` lock для параллельных запусков `Deploy`.

