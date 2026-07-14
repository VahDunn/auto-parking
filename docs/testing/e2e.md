# Браузерные E2E-тесты

Playwright запускает настоящий Chromium против frontend и API за Nginx. Общая
классификация проверок и фактический состав CI описаны в
[обзоре тестирования](README.md).

## Сценарии

| Файл | Сценарий | Поведение по умолчанию |
| --- | --- | --- |
| `tests/e2e/auth.spec.js` | вход manager и загрузка основных экранов | запускается |
| `tests/e2e/vehicle-crud.spec.js` | создание, изменение и удаление автомобиля через UI | пропускается без двух защитных flags |

Обычный `npm run e2e` поэтому выполняет auth smoke, а CRUD показывает как
skipped. Чтобы выполнить оба сценария, CRUD нужно явно разрешить.

## Установка Playwright

Node-зависимости зафиксированы в `package-lock.json`:

```bash
npm ci
npx playwright install chromium
```

Конфигурация находится в `playwright.config.js`. Тестируется только desktop
Chromium; базовый URL по умолчанию — `http://localhost`.

## Изолированный стенд

`docker-compose.e2e.yaml` поднимает отдельные PostGIS, Redis и Kafka, выполняет
миграции и seed, затем запускает backend, frontend и Nginx на
`http://localhost:8081`.

```bash
docker compose \
  -p auto-parking-e2e \
  -f docker-compose.e2e.yaml \
  up -d --build nginx

until curl -fsS http://localhost:8081/api/health >/dev/null; do
  sleep 1
done
```

Стенд использует отдельные named volumes, но они сохраняются между запусками,
пока не выполнен cleanup с `-v`.

## Запуск

Только безопасный auth smoke:

```bash
E2E_BASE_URL=http://localhost:8081 npm run e2e
```

Auth smoke и полный CRUD в одном прогоне:

```bash
E2E_BASE_URL=http://localhost:8081 \
E2E_RUN_CRUD=1 \
E2E_ALLOW_MUTATIONS=1 \
npm run e2e
```

Только CRUD-сценарий; npm script сам устанавливает оба разрешающих flag:

```bash
E2E_BASE_URL=http://localhost:8081 npm run e2e:crud
```

Для отладки доступны headed и UI mode:

```bash
E2E_BASE_URL=http://localhost:8081 npm run e2e:headed
E2E_BASE_URL=http://localhost:8081 npm run e2e:ui
```

## Переменные окружения

| Переменная | Значение по умолчанию | Назначение |
| --- | --- | --- |
| `E2E_BASE_URL` | `http://localhost` | адрес проверяемого Nginx/frontend |
| `E2E_USERNAME` | `superman` | login тестового manager |
| `E2E_PASSWORD` | `superman` | password тестового manager |
| `E2E_RUN_CRUD` | не задана | включает сбор и запуск CRUD-теста при значении `1` |
| `E2E_ALLOW_MUTATIONS` | не задана | подтверждает разрешение менять данные при значении `1` |

Пользователь `superman` создаётся миграциями, а необходимые enterprise и vehicle
model — сервисом `e2e-seed`.

## Защита данных

CRUD-тест начинает работу только при одновременном выполнении условий:

- `E2E_RUN_CRUD=1`;
- `E2E_ALLOW_MUTATIONS=1`;
- hostname в `E2E_BASE_URL` — `localhost`, `127.0.0.1` или loopback IPv6;
- в API доступны хотя бы один enterprise и одна vehicle model.

Эта защита не заменяет отдельную БД. Рекомендуемый target — только compose-стенд
из этого документа.

## Cleanup

Остановить стенд и удалить все его тестовые данные:

```bash
docker compose \
  -p auto-parking-e2e \
  -f docker-compose.e2e.yaml \
  down -v
```

Playwright сохраняет HTML report и диагностические artifacts согласно
`playwright.config.js`; каталоги `playwright-report/` и `test-results/` исключены
из Git.

Browser E2E не входит в текущий GitHub Actions workflow и запускается вручную.
