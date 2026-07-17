# Production deployment

Production разворачивается на одном сервере через Docker Compose. GitHub Actions
копирует на сервер Compose-файл и Nginx config, скачивает заранее собранные образы из
GHCR, применяет миграции и запускает stack.

Это single-server deployment без оркестратора и автоматического failover.

## Источники конфигурации

| Файл | Назначение |
| --- | --- |
| `.github/workflows/deploy.yml` | фактическая последовательность deployment |
| `deploy/docker-compose.prod.yaml` | production services, profiles, volumes и env |
| `deploy/.env.prod.example` | шаблон серверного `.env` |
| `nginx/nginx.conf` | внешний HTTP reverse proxy |
| `docs/ci-cd.md` | CI, образы, inputs и GitHub secrets |

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
- достаточно места для образов и постоянных томов.

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

| Группа       | Переменные |
|--------------| --- |
| Образы       | `IMAGE_REGISTRY`, `IMAGE_NAMESPACE`, `IMAGE_TAG` |
| Основная БД  | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL` |
| Audit DB     | `AUDIT_POSTGRES_DB`, `AUDIT_POSTGRES_USER`, `AUDIT_POSTGRES_PASSWORD` |
| Security     | `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TTL_MINUTES` |
| Runtime      | `APP_ENV=prod`, `DEBUG=false`, `LOG_LEVEL`, `WEB_CONCURRENCY` |
| Integrations | `REDIS_URL`, Kafka consumer groups, `TELEGRAM_BOT_TOKEN` |
| Network      | `HTTP_PORT` |

Пароль внутри `DATABASE_URL` должен совпадать с `POSTGRES_PASSWORD`. Значение
`IMAGE_NAMESPACE` имеет вид `<github-owner>/auto-parking`, без `ghcr.io/` и без
суффикса `/app`.

## Приоритет настроек образов

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

- `IMAGE_NAMESPACE` в серверном `.env` не выбирает образы автоматического деплоя;
- `IMAGE_REGISTRY` в серверном `.env` не меняет `ghcr.io`;
- серверный `.env` в любом случае должен содержать корректный namespace для последующего
  `docker compose ps` и ручных команд, которые workflow запускает без переменной.

Все секреты и рантайм-параметры читаются из server `.env`.
Штатный путь — `.env` рядом с compose-файлом.

## GitHub configuration

Список обязательных и опциональных repository secrets приведён в
[`ci-cd.md`](ci-cd.md#github-secrets).

У workflow два input:

- `image_tag`: `latest` или полный commit SHA;
- `deploy_path`: каталог stack на сервере.

Для предсказуемого результата используйте SHA успешного `CI`, а не `latest`.

## Первый deployment

1. Выполните успешный push в `main` и убедитесь, что все четыре образа с нужным SHA
   появились в GHCR.
2. Подготовьте серверный каталог и `.env`.
3. Создайте GitHub secrets из `ci-cd.md`.
4. Откройте `Actions -> Deploy -> Run workflow`.
5. Укажите `image_tag` и `deploy_path`.

Workflow выполняет следующую последовательность:

1. Проверка репо и вычисление default image namespace.
2. Создание временного SSH ключа и добавление результата `ssh-keyscan` в
   `known_hosts`.
3. Создание `${deploy_path}` и `${deploy_path}/logs` на сервере.
4. Копирование:
   - `deploy/docker-compose.prod.yaml` в `${deploy_path}/docker-compose.yaml`;
   - `nginx/nginx.conf` в `${deploy_path}/nginx.conf`.
5. `docker login ghcr.io` с `GHCR_USERNAME` и `GHCR_TOKEN`.
6. Пулл `bot`, `notifications`, `audit`.
7. Запуск `docker compose run --rm kafka-init`.
8. Запуск `docker compose --profile migrate run --rm migrate`.
9. `docker compose --profile bot --profile notifications --profile audit up -d`.
10. `docker compose ps`.
11. Один запрос `curl -fsS http://localhost/api/health`.

Деплой считается успешным только если все команды, включая health запрос,
завершились с кодом `0`.


Кафка формально запускается дважды (из-за сложной последовательности раскатки),
на второй раз создаёт отсутствующие
топики и может увеличить число партиций, второй проход ничего не убирает.

Compose публикует Nginx через `${HTTP_PORT:-80}`, но workflow всегда проверяет
`http://localhost/api/health`, то есть порт `80`.

Для штатного workflow оставляйте `HTTP_PORT=80`. При другом порте containers могут
успешно запуститься, но финальный шаг завершит deployment ошибкой.

Кроме того, API и Nginx не имеют Compose healthcheck. `up -d` ждёт запуска containers,
но не полной готовности API, а `curl` выполняется один раз без retry. Медленный старт
может дать ложное падение deployment.

## Проверка после

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

Проверка топиков:

```bash
docker compose exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --list
```

## Ручное обновление

Штатный путь — `Deploy`. Если требуется повторить его вручную на сервере, нужно
явно задать те же образы:

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

Не надо запускать обычный `up -d` как замену deployment: production API не зависит от
service `migrate`, поэтому такая команда сама по себе не применяет Alembic migrations.

## Rollback

Автоматического rollback нет. Для возврата application images можно повторно запустить
workflow `Deploy` и указать предыдущий рабочий SHA.

Это безопасно только при совместимой схеме БД. Всегда выполняется
`alembic upgrade head` из выбранного образа и никогда не выполняется `alembic downgrade` - 
уже применённые миграции автоматически не откатываются. Именно поэтому миграции нужно писать
с осторожностью и возможностью роллбека в одну команду, также перед изменениями схемы нужен бэкап и план восстановления.
Все миграции нужно проверять на тестовой базе перед деплоем. 

## Возможные проблемы

### Workflow падает на `ssh-keyscan`

Проверьте `DEPLOY_HOST`, DNS и доступность SSH на порту `22`. Текущий `ssh-keyscan`
не использует `DEPLOY_PORT` (сервер с нестандартным SSH-портом
полностью не поддерживается без изменения шага настройки SSH).

Workflow доверяет ключу, который вернул `ssh-keyscan` во время запуска, и не сверяет
его с заранее сохранённым отпечатком.

### `ssh` или `scp` не подключается

Проверить `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_PORT`, `authorized_keys`, права на
`deploy_path` и доступ пользователя к Docker socket.

### `docker login` или `pull` падает

Проверить:

- `GHCR_USERNAME` и срок действия `GHCR_TOKEN`;
- право `read:packages` и visibility package;
- `IMAGE_NAMESPACE` secret;
- наличие всех четырёх images с выбранным тегом.

`docker login` сохраняет credentials в Docker config пользователя на сервере. Их
нужно отдельно ротировать или удалить при отзыве доступа.

### Compose не читает конфигурацию

Убедитесь, что рядом с `docker-compose.yaml` существуют `.env`, `nginx.conf` и каталог
`logs`. Без вывода значений secrets синтаксис можно проверить так:

```bash
cd /opt/auto-parking
docker compose config -q
```

Если изменились пароли БД после создания постоянного тома, изменение `.env` не
пересоздаст существующую PostgreSQL автоматически.

### Миграции падают

Для диагностики можно посмотреть `DATABASE_URL`, доступность `db` и совместимость Alembic
revision с выбранным image. Не стоит запускать downgrade без backup и отдельного плана.

### Containers запущены, а workflow красный

Проверить `HTTP_PORT`. Финальный request всегда идёт на port `80`. Также возможна гонка
готовности API, потому что запрос выполняется сразу и без ретраев:

```bash
docker compose ps
docker compose logs --tail=100 auto-parking nginx
curl -v http://localhost/api/health
```

### Telegram не работает

Проверить `TELEGRAM_BOT_TOKEN`, `REDIS_URL`, Kafka bootstrap servers и consumer groups,
затем логи `telegram-bot` и `notification-service`. Workflow включает оба профиля при
каждом деплое.

