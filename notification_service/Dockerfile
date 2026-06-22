FROM python:3.12-slim

WORKDIR /service

RUN pip install --upgrade pip \
    && pip install \
      "aiokafka>=0.14.0,<0.15.0" \
      "asyncpg>=0.31.0,<0.32.0" \
      "greenlet>=3.3.1,<4.0.0" \
      "httpx>=0.28.1,<0.29.0" \
      "pydantic-settings>=2.12.0,<3.0.0" \
      "redis>=5.2.1,<6.0.0" \
      "sqlalchemy>=2.0.46,<3.0.0"

COPY notification_service ./notification_service

CMD ["python", "-m", "notification_service.main"]
