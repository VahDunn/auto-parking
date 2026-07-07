# E2E-тесты

Сквозные тесты работают через настоящий браузер Playwright против уже поднятого стенда.

## Запуск

```bash
docker compose up -d db redis kafka kafka-init auto-parking frontend nginx
npm install
npx playwright install chromium
npm run e2e
```

По умолчанию тесты ходят на `http://localhost`. Можно переопределить:

```bash
E2E_BASE_URL=http://localhost npm run e2e
```

Дефолтный пользователь после миграций:

```text
login: superman
password: superman
```

## CRUD-сценарий машины

Полный сценарий создания, редактирования и удаления машины требует, чтобы в БД уже были:

- хотя бы одно предприятие, доступное пользователю;
- хотя бы одна модель машины.

Этот сценарий отключен по умолчанию. Чтобы включить:

```bash
E2E_RUN_CRUD=1 npm run e2e
```

Если данных нет, тест будет пропущен с понятным сообщением.
