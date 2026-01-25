# KIRP Enterprise — Intelligence Operating System

**KIRP is a Controlled Intelligence Layer that unifies personal, team, and organizational knowledge into one living brain — capable of remembering, understanding, reasoning, forecasting, suggesting, executing, and improving itself — with zero leakage and full governance.**

---

## Core Principles (Unbreakable)

1. **Event-Sourced Everything**  
   `Event → RAG → Agent Decision → Governance → Execution → Event`

2. **No Silent Mutation**  
   No state change without an event. Every decision is auditable, explainable, replayable.

3. **Multi-Tenant Isolation (Zero Leakage)**  
   Personal → Shared → Team → Organization. No cross-tenant access unless explicitly granted.

4. **Provider-Agnostic Architecture**  
   LLMs: OpenAI / Anthropic / Ollama · Vector: Qdrant / Pinecone / pgvector · Event Bus: Kafka / Redis Streams

5. **Explainability & Governance First**  
   Every action is logged, explainable, reversible, governed by policy (OPA), optionally human-approved.

---

## Tech Stack

| Layer | Stack |
|-------|--------|
| Backend | FastAPI + Pydantic + SQLAlchemy |
| Event Store | MongoDB |
| Metadata Store | PostgreSQL |
| Vector Store | Qdrant |
| Cache | Redis |
| Event Bus | Kafka (prod) / Redis Streams (dev) |
| Workers | Celery |
| Frontend | Streamlit MVP → Next.js |
| Observability | Prometheus + Grafana + ELK |
| Security | JWT + OPA + Vault |
| LLM | OpenAI / Anthropic / Ollama (pluggable) |

---

## Quick Start

```bash
cp .env.example .env
# Edit .env with your secrets (OpenAI, Notion, Twilio, etc.)
docker-compose up -d --build
# API: http://localhost:8000
# Dashboard: http://localhost:8501
# Governance: http://localhost:8501 (or run separately)
# Mongo Express: http://localhost:8081
# Grafana: http://localhost:3000
# Prometheus: http://localhost:9090
```

See [QUICKSTART.md](QUICKSTART.md) for detailed setup.

---

## Project Structure

```
src/
├── core/
│   ├── event_store.py    # MongoDB event store
│   ├── rag_engine.py     # Qdrant + hybrid search
│   ├── agent_framework.py # Agent registry
│   ├── schema_engine.py  # Tasks, projects, schemas
│   ├── governance.py     # OPA, approvals, audit
│   ├── pipeline.py       # 9-step event processing
│   ├── event_bus.py      # Kafka / Redis Streams
│   └── integrations.py   # Unified clients (Mongo, Redis, Postgres, Cassandra, Kafka, Elastic)
├── auth/
│   ├── tenants.py        # Multi-tenant hierarchy
│   ├── rbac.py           # Roles, permissions
│   └── encryption.py     # Fernet encryption
├── integrations/
│   ├── notion.py         # Bi-directional Notion
│   ├── whatsapp.py       # Twilio / Meta WhatsApp
│   ├── slack.py          # Slack integration
│   ├── email.py          # Email ingest/send
│   └── calendar.py       # Google Calendar
├── agents/
│   ├── pattern_analyzer.py    # Habits, overload detection
│   ├── planner.py             # Daily/weekly planning
│   ├── forecaster.py          # Load prediction
│   ├── risk_opportunity.py    # Risk/opportunity detection
│   ├── schema_structure.py    # Schema building
│   ├── presentation.py        # Live views (Kanban, Timeline)
│   ├── self_improvement.py    # Learning from logs
│   ├── scraper_agent.py       # Web scraping
│   ├── kafka_event_agent.py   # Kafka producer/consumer
│   └── metrics_agent.py       # Metrics to Elasticsearch
├── api/
│   ├── governance.py     # Approvals, audit, policy simulation
│   └── observability.py  # Metrics snapshot, health
├── ui/
│   ├── dashboard.py      # Main Streamlit dashboard
│   ├── governance_dashboard.py # Governance UI
│   ├── api.py            # KIRPApiClient
│   └── realtime.py       # SSE client
└── observability/
    ├── metrics.py        # Prometheus metrics
    ├── traces.py         # OpenTelemetry traces
    └── alerts.py         # Alert engine
```

## Features

### Core Intelligence
- **Event-Sourced Pipeline**: 9-step processing (ingest → store → embed → Qdrant → metadata → publish → agents → governance → execute → emit)
- **RAG Engine**: Hybrid search (semantic + keyword + BM25), multi-hop retrieval, tenant scoping
- **Agent Framework**: 10 built-in agents (Pattern, Planner, Forecaster, Risk/Opportunity, Schema, Presentation, Self-Improvement, Scraper, KafkaEvent, Metrics)
- **Multi-Tenant**: Tenant hierarchy (Root → Private → Shared → Team → Org), zero leakage

### Governance
- **OPA Integration**: Policy-based governance
- **Approval Workflows**: Human-in-the-loop for critical actions
- **Audit Trail**: Full event history, queryable by type/tenant/user
- **Policy Simulation**: Test policy changes before applying

### Integrations
- **Notion**: Bi-directional (ingest pages → Events, create tasks → Actions)
- **WhatsApp**: Twilio / Meta (webhooks → Events, send messages → Actions)
- **Slack, Email, Calendar**: Inbound + outbound

### Observability
- **Prometheus**: Metrics collection
- **Grafana**: Dashboards
- **Elasticsearch**: Logs, metrics, search
- **OpenTelemetry**: Distributed tracing

### Infrastructure
- **Event Bus**: Kafka (prod) / Redis Streams (dev)
- **Workers**: Celery for async tasks
- **Storage**: MongoDB (events), PostgreSQL (metadata), Qdrant (vectors), Cassandra (time-series), Redis (cache)

---

## License

Proprietary — KIRP Enterprise.
