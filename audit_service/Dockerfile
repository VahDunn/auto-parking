FROM python:3.12-slim

WORKDIR /service

RUN pip install --upgrade pip \
    && pip install \
      "aiokafka>=0.14.0,<0.15.0" \
      "pydantic-settings>=2.12.0,<3.0.0" \
      "redis>=5.2.1,<6.0.0"

COPY audit_service ./audit_service

CMD ["python", "-m", "audit_service.main"]
