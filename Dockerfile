FROM python:3.12-slim
LABEL authors="vladislavmorozov"

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY auto_parking ./auto_parking

RUN pip install --upgrade pip \
    && pip install .

EXPOSE 8000

CMD ["uvicorn", "auto_parking.main:app", "--host", "0.0.0.0", "--port", "8000"]