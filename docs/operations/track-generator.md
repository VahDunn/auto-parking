# GPS Track Generator

## Генерация GPS-треков

Для проекта добавлена CLI-утилита на Typer:

    auto_parking/minor_utilities/track_generator.py

Она умеет: - генерировать live-трек для одной машины; - генерировать
live-треки для всех машин предприятия; - очищать старые точки.

## Подготовка

Убедиться, что контейнеры подняты:

    docker-compose up -d --build

## Очистка точек

Удалить все точки:

    docker-compose exec auto-parking python -m auto_parking.minor_utilities.track_generator track-clear --all

Удалить точки одной машины:

    docker-compose exec auto-parking python -m auto_parking.minor_utilities.track_generator track-clear --vehicle-id 3214

## Генерация трека для одной машины

    docker-compose exec auto-parking python -m auto_parking.minor_utilities.track_generator track-generate-live \
      --vehicle-id 3214 \
      --radius-km 3 \
      --track-length-km 2 \
      --interval-sec 5 \
      --clear-before

С бесконечной генерацией:

    docker-compose exec auto-parking python -m auto_parking.minor_utilities.track_generator track-generate-live \
      --vehicle-id 3214 \
      --radius-km 3 \
      --track-length-km 2 \
      --interval-sec 5 \
      --clear-before \
      --loop

## Генерация для всего предприятия

    docker-compose exec auto-parking python -m auto_parking.minor_utilities.track_generator track-generate-enterprise-live \
      --enterprise-id 2 \
      --radius-km 3 \
      --track-length-km 2 \
      --interval-sec 5 \
      --clear-before

## Просмотр движения в реальном времени

1. Открыть приложение по адресу `http://localhost`, войти и выбрать предприятие.
2. Убедиться, что над картой показано `Live: подключено`.
3. В отдельном терминале запустить генерацию:

       docker-compose exec auto-parking python -m auto_parking.minor_utilities.track_generator track-generate-enterprise-live \
         --enterprise-id 2 \
         --vehicles-count 10 \
         --interval-sec 1

Новые GPS-точки публикуются в Kafka topic `auto-parking.gps.events`, затем проходят через RxPY pipeline и приходят на карту по WebSocket. Для каждой машины на карте создается отдельный движущийся маркер.

## Проверка через API

JSON:

    curl "http://localhost:8001/api/vehicles/3214/track?date_from=2026-04-01T00:00:00Z&date_to=2026-04-30T23:59:59Z&format=json" \
      -H "Authorization: Bearer <TOKEN>"

GeoJSON:

    curl "http://localhost:8001/api/vehicles/3214/track?date_from=2026-04-01T00:00:00Z&date_to=2026-04-30T23:59:59Z&format=geojson" \
      -H "Authorization: Bearer <TOKEN>"

## Проверка через БД

    docker-compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
    SELECT
        vehicle_id,
        recorded_at_utc,
        ST_X(position) AS lon,
        ST_Y(position) AS lat
    FROM vehicle_gps_point
    WHERE vehicle_id = 3214
    ORDER BY recorded_at_utc DESC
    LIMIT 10;
    "

## Остановка

    Ctrl+C
