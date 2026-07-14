# Генератор GPS-треков

CLI `auto_parking.minor_utilities.track_generator` создаёт точки и поездки в
основной БД, публикует live GPS events в Kafka и тем самым обновляет карту через
WebSocket. Команды изменяют данные; используйте development/test окружение.

## Подготовка

Запустите локальный стенд и убедитесь, что нужные `vehicle_id`/`enterprise_id`
существуют. Общая инструкция находится в
[локальной разработке](../development/local-setup.md).

Посмотреть все параметры:

```bash
docker compose exec auto-parking \
  python -m auto_parking.minor_utilities.track_generator --help
```

## Одна машина

```bash
docker compose exec auto-parking \
  python -m auto_parking.minor_utilities.track_generator \
  track-generate-live \
  --vehicle-id 3214 \
  --radius-km 3 \
  --track-length-km 2 \
  --interval-sec 5 \
  --clear-before \
  --loop
```

Без `--loop` генератор завершится после одного маршрута. Для воспроизводимого
маршрута используйте `--seed`; `--no-osrm` отключает внешний OSRM.

## Предприятие

```bash
docker compose exec auto-parking \
  python -m auto_parking.minor_utilities.track_generator \
  track-generate-enterprise-live \
  --enterprise-id 2 \
  --vehicles-count 10 \
  --radius-km 3 \
  --track-length-km 2 \
  --interval-sec 1 \
  --clear-before
```

Остановите непрерывную генерацию через `Ctrl+C`.

## Очистка

Удалить поездки и точки одной машины:

```bash
docker compose exec auto-parking \
  python -m auto_parking.minor_utilities.track_generator \
  track-clear --vehicle-id 3214
```

Удаление данных всех машин требует явного флага:

```bash
docker compose exec auto-parking \
  python -m auto_parking.minor_utilities.track_generator \
  track-clear --all
```

## Проверка

После авторизации откройте приложение и убедитесь, что карта показывает
`Live: подключено`. Исторические точки можно запросить через Nginx:

```bash
curl --get 'http://localhost/api/vehicles/3214/track' \
  -H 'Authorization: Bearer <TOKEN>' \
  --data-urlencode 'date_from=2026-04-01T00:00:00Z' \
  --data-urlencode 'date_to=2026-04-30T23:59:59Z' \
  --data-urlencode 'format=json'
```

Последние строки БД:

```bash
docker compose exec db sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
    SELECT vehicle_id, recorded_at_utc,
           ST_X(position) AS lon, ST_Y(position) AS lat
    FROM vehicle_gps_point
    ORDER BY recorded_at_utc DESC
    LIMIT 10;
  "'
```
