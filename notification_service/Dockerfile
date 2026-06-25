FROM python:3.12-slim

WORKDIR /service

RUN pip install --upgrade pip \
    && pip install \
      "aiokafka>=0.14.0,<0.15.0" \
      "httpx>=0.28.1,<0.29.0" \
      "pydantic-settings>=2.12.0,<3.0.0" \
      "redis>=5.2.1,<6.0.0"

COPY notification_service ./notification_service
COPY event_bus ./event_bus

CMD ["python", "-m", "notification_service.main"]
