# RunMyDocker deployment — KIRP API single container

Run only the KIRP API in one container (port **8000**). All infrastructure (MongoDB, Postgres, Redis, Qdrant, Kafka, etc.) is provided by your **cloud/managed services** and configured via environment variables.

## 1. Build and run locally (test)

```bash
# Use cloud env template (copy and fill your real URIs)
cp .env.runmydocker .env
# Edit .env with your MongoDB Atlas, Postgres, Redis, Qdrant cloud URIs, etc.

docker build -f Dockerfile.api -t kirp-api:cloud .
docker run -p 8000:8000 --env-file .env kirp-api:cloud
```

## 2. RunMyDocker setup

1. **Repository**: Point RunMyDocker at this repo and branch.
2. **Dockerfile**: Use `Dockerfile.api` (build context = repo root).
3. **Port**: Expose **8000** only.
4. **Environment**: In RunMyDocker’s env configuration, set variables from `.env.runmydocker` (or paste from your filled `.env`). All connections must be cloud URIs:
   - `MONGO_URI` — e.g. MongoDB Atlas `mongodb+srv://...`
   - `POSTGRES_URI` — e.g. `postgresql+asyncpg://user:pass@host:5432/kirp`
   - `REDIS_URL` — e.g. `redis://:pass@host:6379/0`
   - `QDRANT_URL` — your Qdrant Cloud URL
   - `OPENAI_API_KEY`, `JWT_SECRET`, etc.

No local MongoDB, Postgres, Redis, Qdrant, Kafka, or other services run in the same host; the API expects them via env.

## 3. Behaviour

- **Startup**: The API starts without connecting to any external service (lazy connect). It will not hang or crash if a service is temporarily down.
- **First request**: When an endpoint needs a store (e.g. `/health`, `/api/v1/ingest`), it connects to the relevant service. If that fails, that request returns 503; the process stays up and will retry on the next request.
- **Health**:
  - `GET /healthz` — always 200 (no dependency check). Use this for RunMyDocker/load balancer health checks.
  - `GET /health` — checks EventStore and RAG; returns 503 if they are unavailable.

## 4. Backup

A backup of the original files (before cloud changes) is in `backup_pre_runmydocker/` (`.env`, `Dockerfile.api`, `requirements.txt`, `docker-compose.yml`, `src/main.py`, `src/core/*`, `src/api/*`, all Dockerfiles). Restore by copying back as needed.
