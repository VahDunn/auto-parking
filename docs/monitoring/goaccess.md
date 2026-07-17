# GoAccess и access logs

GoAccess строит локальные HTML-отчёты из двух независимых источников. Он не
входит в Docker Compose и устанавливается отдельно.

## Лог приложения

FastAPI пишет `logs/app-access.log` в формате с таймштампом и дополнительной
длительностью запроса в миллисекундах.

```bash
goaccess logs/app-access.log \
  --no-global-config \
  -p monitoring/goaccess/app.conf \
  -o logs/goaccess-app-report.html
```

Путь задаётся `APP_ACCESS_LOG_PATH`; локальный Compose монтирует каталог `logs`
в API container.

## Лог Nginx

Nginx пишет access log в stdout в формате `goaccess_combined`. Сначала сохраните
его без Compose prefix, затем постройте отчёт:

```bash
docker compose logs --no-color nginx \
  | sed -E 's/^auto_parking_nginx[[:space:]]+\\| //' \
  > logs/nginx-access.log

goaccess logs/nginx-access.log \
  --no-global-config \
  -p monitoring/goaccess/nginx.conf \
  -o logs/goaccess-nginx-report.html
```

Форматы хранятся в `monitoring/goaccess`. Отчёты и исходные логи находятся в
gitignored-каталоге `logs`.
