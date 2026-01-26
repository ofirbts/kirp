# KIRP Enterprise — Quick Start Guide

## Prerequisites

- Docker & Docker Compose
- `.env` file (copy from `.env.example` and fill with your credentials)

## Start Full Stack

```bash
cd kirp-enterprise
cp .env.example .env
# Edit .env with your real credentials (OpenAI, Notion, Twilio, etc.)
docker-compose up -d --build
```

## Services

| Service | URL | Description |
|---------|-----|-------------|
| **KIRP API** | http://localhost:8000 | FastAPI main app |
| **KIRP Dashboard** | http://localhost:8501 | Streamlit UI |
| **Governance Dashboard** | http://localhost:8501 (tab) | Approvals, audit, policy |
| **Mongo Express** | http://localhost:8081 | MongoDB admin UI |
| **Grafana** | http://localhost:3000 | Observability (admin/admin) |
| **Prometheus** | http://localhost:9090 | Metrics |
| **Elasticsearch** | http://localhost:9200 | Search & logs |
| **Kafka** | localhost:9092 | Event bus |

## Verify

```bash
# Check API health
curl http://localhost:8000/health

# Check agents
curl http://localhost:8000/api/v1/agents

# Ingest test content
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test",
    "space_id": "private",
    "user_id": "user1",
    "content": "Test knowledge entry",
    "source": "api"
  }'
```

## Governance Dashboard

Run separately (or access via main dashboard):

```bash
streamlit run src/ui/governance_dashboard.py --server.port 8502
```

Access: http://localhost:8502

## Stop

```bash
docker-compose down
# Or with volumes:
docker-compose down -v
```

## Bootcamp (Remote) Config

To use Bootcamp services instead of local Docker:

1. Set `BOOTCAMP_*` env vars in `.env`
2. Update `src/core/integrations.py` calls to use `use_bootcamp=True`
3. Or create a separate `.env.bootcamp` file

## Troubleshooting

- **Kafka not starting**: Wait 60s for Zookeeper + Kafka to initialize
- **Cassandra slow**: First startup creates keyspace; wait 30-60s
- **Elasticsearch OOM**: Reduce `ES_JAVA_OPTS` in docker-compose.yml
- **API 503**: Check MongoDB, Qdrant, Redis health
