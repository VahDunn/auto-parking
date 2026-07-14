# Миграции Alembic

Миграции основной PostgreSQL/PostGIS базы находятся в `alembic/versions` и
применяются образом `app`. Модели audit-service создаются самим сервисом и не
входят в эту цепочку Alembic.

## Локальный Compose

При первом запуске сервис `migrate` автоматически выполняет:

```bash
alembic upgrade head
```

Повторный ручной запуск:

```bash
docker compose run --rm migrate
```

Текущая и целевая ревизии:

```bash
docker compose run --rm migrate alembic current
docker compose run --rm migrate alembic heads
```

## Создание миграции

Установите зависимости, задайте `DATABASE_URL` для отдельной development-БД и
выполните:

```bash
poetry run alembic revision --autogenerate -m "describe change"
```

Перед применением обязательно проверьте созданный файл: autogenerate не знает
намерений разработчика, может неверно распознать rename и не покрывает перенос
данных.

```bash
poetry run alembic upgrade head
poetry run alembic current
```

## Правила изменения схемы

- одна миграция должна иметь понятные `upgrade()` и `downgrade()`;
- миграция не должна зависеть от локальных данных;
- новые индексы и ограничения проверяются интеграционными тестами;
- destructive-операции разделяются на совместимые этапы, если старая и новая
  версии приложения могут работать одновременно;
- миграцию нужно проверить на disposable PostGIS БД до merge.

Production workflow применяет `upgrade head` перед перезапуском приложения.
Автоматического downgrade при rollback image нет; совместимость и план отката
описаны в [деплое](../deployment.md).
