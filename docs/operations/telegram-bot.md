# Telegram-бот и уведомления

`telegram-bot` — отдельный процесс из основного образа. Он обращается к FastAPI
по HTTP и после `/login` сохраняет связь `user_id -> chat_id` в Redis.
`notification-service` читает события машин из Kafka и использует эту связь для
отправки уведомлений.

## Запуск

Создайте бота через BotFather и задайте в `.env`:

```dotenv
TELEGRAM_BOT_TOKEN=<telegram-token>
```

Запустите bot и consumer:

```bash
docker compose \
  --profile bot \
  --profile notifications \
  up -d telegram-bot notification-service
```

Для запуска процесса вне Docker нужны доступные с host `BOT_API_BASE_URL` и
`REDIS_URL`:

```bash
poetry run python -m auto_parking.bot.main
```

## Команды

```text
/login <логин> <пароль>
/mileage_vehicle_day <начало_номера> <YYYY-MM-DD>
/mileage_vehicle_month <начало_номера> <YYYY-MM>
/mileage_enterprise_day <начало_названия> <YYYY-MM-DD>
/mileage_enterprise_month <начало_названия> <YYYY-MM>
```

Обычный текст бот возвращает эхом.

## Диагностика

```bash
docker compose logs --tail=120 telegram-bot notification-service
docker compose exec redis \
  redis-cli --scan --pattern 'bot:telegram:user:*'
```

Если сообщения после vehicle event не приходят, проверьте, что пользователь
выполнил `/login`, consumer подключился к Kafka и у него совпадает
`KAFKA_NOTIFICATION_CONSUMER_GROUP`.
