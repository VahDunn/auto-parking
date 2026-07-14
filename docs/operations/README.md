# Эксплуатация и служебные задачи

Раздел содержит только инструкции для уже настроенного окружения. Запуск с нуля
описан в [локальной разработке](../development/local-setup.md), production — в
[деплое](../deployment.md), наблюдаемость — в [monitoring](../monitoring/README.md).

| Задача | Документ |
| --- | --- |
| Создать и применить миграцию БД | [Alembic](alembic.md) |
| Запустить Telegram-бота и notification consumer | [Telegram bot](telegram-bot.md) |
| Сгенерировать live GPS-треки | [Track generator](track-generator.md) |

Для диагностики production-сервера, rollback и проверки health используйте
[инструкцию по деплою](../deployment.md), чтобы одни и те же команды не
поддерживались в нескольких местах.
