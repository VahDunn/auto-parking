# GoAccess

## Application access log

Приложение пишет встроенный access log в `logs/app-access.log`.
Формат совместим с GoAccess и не зависит от локали:

```text
127.0.0.1 - - [1780738445] "GET /api/health HTTP/1.1" 200 15 "-" "curl/8.7.1" 12.345
```

Последнее поле - длительность запроса в миллисекундах.

Собрать отчет:

```bash
goaccess logs/app-access.log \
  --no-global-config \
  -p monitoring/goaccess/app.conf \
  -o logs/goaccess-app-report.html
```

## Nginx access log

Nginx пишет access log в формате `goaccess_combined` с unix timestamp:

```text
127.0.0.1 - - [1780738445] "GET /api/health HTTP/1.1" 200 15 "-" "curl/8.7.1"
```

Такой формат не зависит от локали терминала и не ломается на датах вида
`22/May/2026`.

Собрать отчет из docker logs:

```bash
docker-compose logs --no-color nginx \
  | sed -E 's/^auto_parking_nginx[[:space:]]+\\| //' \
  > logs/nginx-access.log

goaccess logs/nginx-access.log \
  --no-global-config \
  -p monitoring/goaccess/nginx.conf \
  -o logs/goaccess-nginx-report.html
```

Для старых логов nginx в дефолтном формате `22/May/2026` нужен старый
combined-конфиг или запуск с `LC_ALL=C`.
