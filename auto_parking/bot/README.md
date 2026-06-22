# Telegram bot

Бот запускается отдельным процессом и дергает существующее HTTP API проекта.

После успешного `/login` бот сохраняет связь `user_id -> telegram chat_id` в Redis. Эту связь использует отдельный `notification-service`, чтобы отправлять Telegram-уведомления залогиненным менеджерам по событиям из Kafka.

## Запуск

1. Создать Telegram-бота через BotFather.
2. Положить токен в `.env`:

```env
TELEGRAM_BOT_TOKEN=123456:telegram-token
```

3. Запустить:

```bash
python -m auto_parking.bot.main
```

Или через Docker Compose:

```bash
docker compose --profile bot up telegram-bot
```

Для запуска вместе с Kafka notification-service:

```bash
EVENT_BUS_BACKEND=kafka docker compose --profile bot --profile notifications up -d --build telegram-bot notification-service
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
