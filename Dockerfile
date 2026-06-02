# KIRP Enterprise API — single container for RunMyDocker / cloud
# Exposes port 8000 only. All infra (Mongo, Postgres, Redis, Qdrant, Kafka) via env.

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install "uvicorn[standard]" websockets wsproto


COPY . .
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
