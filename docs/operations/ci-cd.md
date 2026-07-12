# CI/CD в проекте Auto Parking

Этот документ объясняет, как в проекте устроен CI/CD, какие файлы за это отвечают, что надо создать в GitHub и на сервере, где указывать реальные адреса, токены и секреты.

## Что реализовано

В проекте настроена простая single-server CI/CD схема:

```mermaid
flowchart LR
    Commit["git commit"] --> Hook["local hook: ruff"]
    Push["git push / PR"] --> CI["GitHub Actions: ruff + pytest"]
    CI --> Main{"branch main?"}
    Main -->|"yes"| Build["Build Docker images"]
    Build --> PushImages["Push to private GHCR"]
    PushImages --> Deploy["Manual Deploy workflow"]
    Deploy --> Server["SSH server"]
    Server --> Compose["docker compose pull + migrate + up"]
```

Политика такая:

| Этап | Что запускается | Где запускается | Зачем |
| --- | --- | --- | --- |
| Commit | `ruff check .` | локально | быстро ловить стиль и простые ошибки до commit |
| Push / PR | `ruff check .` + `pytest tests` | GitHub Actions | не пускать сломанный код дальше |
| Push в `main` | сборка и push Docker images | GitHub Actions | подготовить deployable images |
| Deploy | `docker compose pull`, миграции, `up -d` | сервер по SSH | обновить работающий стенд |

## Какие файлы добавлены

### `githooks/pre-commit`

Локальный hook на commit.

Запускает:

```bash
poetry run ruff check .
```

Если `ruff` падает, commit останавливается.

### `.github/workflows/ci.yml`

Основной CI workflow.

Делает две вещи:

1. На любой push и pull request запускает `ruff` и `pytest`.
2. На push в `main`, если проверки прошли, собирает Docker images и пушит их в GitHub Container Registry.

### `.github/workflows/deploy.yml`

Ручной deploy workflow.

Он не запускается автоматически на каждый push. Его нужно запускать руками из GitHub Actions.

Почему вручную: для учебного проекта и одного сервера безопаснее сначала явно выбрать момент деплоя, чем автоматически выкатывать каждый push в `main`.

### `deploy/docker-compose.prod.yaml`

Production compose-файл.

Отличие от локального `docker-compose.yaml`: в нем нет `build`, только готовые `image`.

То есть локально мы можем собирать из исходников, а на сервере сервер просто скачивает готовые образы из registry.

### `deploy/.env.prod.example`

Пример production `.env`.

Это шаблон. Реальный `.env` должен лежать только на сервере и не должен попадать в Git.

### `docs/operations/ci-cd.md`

Этот документ.

## Локальный commit hook

Hook уже лежит в проекте:

```text
githooks/pre-commit
```

Чтобы Git начал его использовать, один раз выполни:

```bash
git config core.hooksPath githooks
chmod +x githooks/pre-commit
```

После этого при каждом commit будет запускаться:

```bash
poetry run ruff check .
```

Проверить руками:

```bash
githooks/pre-commit
```

## CI на push и pull request

Workflow:

```text
.github/workflows/ci.yml
```

На push и pull request запускается job `checks`:

```bash
poetry install --with dev --no-interaction
poetry run ruff check .
poetry run pytest tests
```

То есть на push проверяется уже не только стиль, но и тесты.

## Docker images

После push в `main`, если `ruff` и `pytest` прошли, job `images` собирает Docker images.

Registry:

```text
ghcr.io
```

GHCR - GitHub Container Registry. Его можно держать private. Делать образы публичными не нужно.

По умолчанию namespace строится так:

```text
<github-owner>/auto-parking
```

Например, если репозиторий принадлежит пользователю `vl-morozov`, получится:

```text
ghcr.io/vl-morozov/auto-parking/app
ghcr.io/vl-morozov/auto-parking/notification-service
ghcr.io/vl-morozov/auto-parking/audit-service
ghcr.io/vl-morozov/auto-parking/frontend
```

Каждый образ пушится с двумя тегами:

```text
<commit-sha>
latest
```

Пример:

```text
ghcr.io/vl-morozov/auto-parking/app:2f8c...
ghcr.io/vl-morozov/auto-parking/app:latest
```

Тег `latest` удобно деплоить руками. Тег с commit SHA удобен, если нужно точно понимать, какая версия кода выкачена на сервер.

## Какие images используются

| Image | Dockerfile | Для чего |
| --- | --- | --- |
| `app` | `Dockerfile` | основной API, Telegram-бот, Alembic migrations, `kafka-init` |
| `notification-service` | `notification_service/Dockerfile` | микросервис Telegram-уведомлений |
| `audit-service` | `audit_service/Dockerfile` | микросервис аудита |
| `frontend` | `frontend/Dockerfile` | статический frontend на nginx |

Почему `app` используется сразу для нескольких процессов:

- код API, бота, Alembic и `event_bus.init_topics` лежит в одном основном образе;
- отличается только команда запуска;
- не нужно плодить почти одинаковые Dockerfile.

## Что надо создать в GitHub

Открой:

```text
GitHub repository -> Settings -> Secrets and variables -> Actions
```

Там нужно создать repository secrets.

### Обязательные secrets для deploy

```text
DEPLOY_HOST
DEPLOY_USER
DEPLOY_SSH_KEY
GHCR_USERNAME
GHCR_TOKEN
```

Что это значит:

| Secret | Где взять | Пример |
| --- | --- | --- |
| `DEPLOY_HOST` | IP или домен сервера | `203.0.113.10` |
| `DEPLOY_USER` | пользователь на сервере | `deploy` |
| `DEPLOY_SSH_KEY` | приватный SSH-ключ | содержимое `~/.ssh/auto_parking_deploy` |
| `GHCR_USERNAME` | GitHub username | `vl-morozov` |
| `GHCR_TOKEN` | GitHub token для pull private images | PAT с `read:packages` |

### Опциональные secrets

```text
DEPLOY_PORT
IMAGE_NAMESPACE
```

| Secret | Когда нужен | Значение по умолчанию |
| --- | --- | --- |
| `DEPLOY_PORT` | если SSH не на 22 порту | `22` |
| `IMAGE_NAMESPACE` | если images лежат не в `<github-owner>/auto-parking` | `<github-owner>/auto-parking` |

### Где хранить Telegram token, JWT secret и пароли БД

Не в GitHub Actions secrets для этого проекта.

Их лучше хранить в production `.env` на сервере:

```text
/opt/auto-parking/.env
```

GitHub Actions не должен знать пароль от production PostgreSQL, Telegram token и JWT secret, если он просто деплоит compose-файл и images.

Исключение: если потом захочется генерировать `.env` прямо из GitHub Actions. Сейчас так не сделано намеренно.

## GHCR token

Для deploy нужен token, с которым сервер сможет скачать private images из GHCR.

Минимально нужен доступ:

```text
read:packages
```

Если GitHub попросит доступ к private repository packages, может понадобиться еще доступ к repo. Это зависит от настроек репозитория и package visibility.

Этот token указывается в GitHub secret:

```text
GHCR_TOKEN
```

На сервер он не сохраняется в репозитории. Deploy workflow передает его в:

```bash
docker login ghcr.io --password-stdin
```

## Что надо создать на сервере

На сервере должны быть:

```bash
docker
docker compose
curl
```

Проверь:

```bash
docker --version
docker compose version
curl --version
```

### Пользователь для deploy

Лучше создать отдельного пользователя, например:

```bash
sudo adduser deploy
sudo usermod -aG docker deploy
```

После добавления в группу `docker` надо перелогиниться.

### SSH key

На локальной машине можно создать ключ:

```bash
ssh-keygen -t ed25519 -C "auto-parking-deploy" -f ~/.ssh/auto_parking_deploy
```

Публичный ключ положить на сервер:

```bash
ssh-copy-id -i ~/.ssh/auto_parking_deploy.pub deploy@<server-ip>
```

Приватный ключ положить в GitHub secret:

```text
DEPLOY_SSH_KEY
```

### Директория проекта на сервере

Например:

```bash
sudo mkdir -p /opt/auto-parking
sudo chown deploy:deploy /opt/auto-parking
```

Именно этот путь потом указывается в deploy workflow input:

```text
deploy_path: /opt/auto-parking
```

## Production `.env`

На сервере должен лежать файл:

```text
/opt/auto-parking/.env
```

Шаблон:

```text
deploy/.env.prod.example
```

Скопировать:

```bash
cp deploy/.env.prod.example /opt/auto-parking/.env
```

Потом открыть и заменить все `change-me`.

Главные поля:

```env
IMAGE_REGISTRY=ghcr.io
IMAGE_NAMESPACE=your-github-user/auto-parking
IMAGE_TAG=latest

POSTGRES_DB=auto_parking
POSTGRES_USER=auto_parking
POSTGRES_PASSWORD=change-me
DATABASE_URL=postgresql+asyncpg://auto_parking:change-me@db:5432/auto_parking

JWT_SECRET_KEY=change-me
TELEGRAM_BOT_TOKEN=change-me

AUDIT_POSTGRES_DB=audit_db
AUDIT_POSTGRES_USER=audit_user
AUDIT_POSTGRES_PASSWORD=change-me
```

Где указывать конкретные данные:

| Данные | Где указывать |
| --- | --- |
| IP сервера | GitHub secret `DEPLOY_HOST` |
| SSH user | GitHub secret `DEPLOY_USER` |
| SSH private key | GitHub secret `DEPLOY_SSH_KEY` |
| GitHub token для registry | GitHub secret `GHCR_TOKEN` |
| Docker image namespace | server `.env` или GitHub secret `IMAGE_NAMESPACE` |
| PostgreSQL password | server `.env` |
| JWT secret | server `.env` |
| Telegram bot token | server `.env` |
| HTTP port | server `.env`, поле `HTTP_PORT` |
| количество uvicorn workers | server `.env`, поле `WEB_CONCURRENCY` |

## Production compose

Production compose лежит здесь:

```text
deploy/docker-compose.prod.yaml
```

Deploy workflow копирует его на сервер как:

```text
/opt/auto-parking/docker-compose.yaml
```

Также workflow копирует:

```text
nginx/nginx.conf -> /opt/auto-parking/nginx.conf
```

Production compose поднимает:

- `db`;
- `audit-db`;
- `redis`;
- `kafka`;
- `kafka-init`;
- `auto-parking`;
- `telegram-bot`;
- `notification-service`;
- `audit-service`;
- `frontend`;
- `nginx`.

Профили:

```text
bot
notifications
audit
migrate
```

Deploy workflow поднимает основные профили:

```bash
docker compose --profile bot --profile notifications --profile audit up -d
```

Миграции запускаются отдельно:

```bash
docker compose --profile migrate run --rm migrate
```

## Первый запуск CI

После push в GitHub workflow `CI` должен автоматически запуститься.

Ожидаемое:

1. Job `checks` проходит.
2. Если это push в `main`, job `images` собирает и пушит images.

Если push не в `main`, Docker images не пушатся. Это специально: feature branches проверяются тестами, но не публикуют артефакты.

## Первый deploy

1. Убедиться, что images уже собраны в GHCR.

   Для этого нужен успешный push в `main`.

2. Убедиться, что на сервере есть:

   ```text
   /opt/auto-parking/.env
   ```

3. В GitHub открыть:

   ```text
   Actions -> Deploy -> Run workflow
   ```

4. Указать:

   ```text
   image_tag: latest
   deploy_path: /opt/auto-parking
   ```

5. Workflow сделает:

   ```bash
   docker login ghcr.io
   docker compose pull
   docker compose run --rm kafka-init
   docker compose --profile migrate run --rm migrate
   docker compose --profile bot --profile notifications --profile audit up -d
   docker compose ps
   curl -fsS http://localhost/api/health
   ```

Если `/api/health` вернул `200`, deploy считается успешным.

## Как деплоить конкретный commit

В workflow `CI` images пушатся с тегом commit SHA.

Можно открыть GitHub Actions, найти commit SHA и запустить deploy с:

```text
image_tag: <commit-sha>
```

Это полезно, если нужно деплоить не `latest`, а конкретную сборку.

## Как откатиться

Если известен предыдущий рабочий SHA:

1. Открыть workflow `Deploy`.
2. Запустить его с:

   ```text
   image_tag: <previous-good-sha>
   ```

3. Compose скачает старые images и перезапустит сервисы.

Ограничение: миграции БД назад автоматически не откатываются. Если миграция несовместима, rollback надо продумывать отдельно.

## Команды на сервере

Статус:

```bash
cd /opt/auto-parking
docker compose --profile bot --profile notifications --profile audit ps
```

Логи:

```bash
docker compose logs --tail=100 auto-parking
docker compose logs --tail=100 notification-service
docker compose logs --tail=100 audit-service
docker compose logs --tail=100 telegram-bot
```

Ручной pull и restart:

```bash
cd /opt/auto-parking
docker compose --profile bot --profile notifications --profile audit pull
docker compose --profile bot --profile notifications --profile audit up -d
```

Проверка health:

```bash
curl -fsS http://localhost/api/health
```

Проверка Kafka topics:

```bash
docker compose exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --list
```

Проверка consumer lag:

```bash
docker compose exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --group auto-parking-notification-service
```

## Типовые проблемы

### Commit не проходит

Причина: локальный `ruff` нашел ошибку.

Проверить:

```bash
poetry run ruff check .
```

Автоисправление:

```bash
poetry run ruff check . --fix
```

### GitHub CI падает на tests

Проверить локально:

```bash
poetry run pytest tests
```

Если локально проходит, а в CI нет, смотреть разницу окружения: Python version, env vars, platform.

Интеграционные тесты помечены `integration` и по умолчанию локально пропускаются, чтобы обычный `pytest` не требовал Postgres/PostGIS.

Запуск руками:

```bash
docker run --rm -d --name auto-parking-it-postgis \
  -e POSTGRES_DB=auto_parking_test \
  -e POSTGRES_USER=auto_parking \
  -e POSTGRES_PASSWORD=change-me \
  -p 55432:5432 \
  postgis/postgis:16-3.4

RUN_INTEGRATION=1 \
TEST_DATABASE_URL=postgresql+asyncpg://auto_parking:change-me@127.0.0.1:55432/auto_parking_test \
DATABASE_URL=postgresql+asyncpg://auto_parking:change-me@127.0.0.1:55432/auto_parking_test \
AUDIT_DATABASE_URL=postgresql+asyncpg://auto_parking:change-me@127.0.0.1:55432/auto_parking_test \
JWT_SECRET_KEY=test-secret \
poetry run pytest tests/integration

docker stop auto-parking-it-postgis
```

В GitHub Actions PostGIS поднимается как service container, поэтому там интеграционные тесты запускаются автоматически.

### Deploy не может подключиться по SSH

Проверить:

- `DEPLOY_HOST`;
- `DEPLOY_USER`;
- `DEPLOY_PORT`;
- `DEPLOY_SSH_KEY`;
- открыт ли SSH-порт на сервере;
- есть ли публичный ключ в `~/.ssh/authorized_keys` у deploy user.

### `docker login ghcr.io` падает

Проверить:

- `GHCR_USERNAME`;
- `GHCR_TOKEN`;
- есть ли у token право `read:packages`;
- доступен ли package этому пользователю;
- private/public visibility package.

### `docker compose pull` не находит image

Проверить:

- `IMAGE_NAMESPACE`;
- `IMAGE_TAG`;
- есть ли такой image в GHCR;
- прошла ли job `images` в workflow `CI`.

### Приложение поднялось, но API не отвечает

Проверить:

```bash
docker compose logs --tail=100 auto-parking
docker compose logs --tail=100 nginx
docker compose ps
```

Также проверить `.env`:

- `DATABASE_URL`;
- `JWT_SECRET_KEY`;
- `REDIS_URL`;
- `KAFKA_BOOTSTRAP_SERVERS`.

### Notification service не отправляет Telegram

Проверить:

```bash
docker compose logs --tail=100 notification-service
docker compose logs --tail=100 telegram-bot
```

И убедиться, что менеджер логинился в Telegram-боте:

```bash
docker compose exec redis redis-cli --scan --pattern 'bot:telegram:user:*'
```

## Почему не делаем сложнее

Сейчас схема специально простая:

- один сервер;
- Docker Compose;
- private GHCR;
- ручной deploy;
- Kafka/Postgres/Redis рядом в compose.

Для текущего проекта этого достаточно.

Что можно добавить потом:

- staging и production окружения отдельно;
- автоматический deploy после merge в `main`;
- rollback workflow;
- Sentry;
- backup PostgreSQL;
- отдельный managed PostgreSQL;
- отдельный managed Kafka;
- zero-downtime deploy;
- Kubernetes.

Но это следующий уровень. Сейчас главная цель - чтобы каждый push проверялся, images собирались одинаково, а deploy выполнялся воспроизводимо одной кнопкой.
