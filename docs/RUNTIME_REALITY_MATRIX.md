# Runtime Reality Matrix

Authoritative mapping between **narrative** (brief, whitepaper, diagrams, `UNIFIED_ARCHITECTURE.md`, READMEs, compose) and **what runs in this repository**. Status is derived from **code + deploy configs** as of the audit that produced this file—not from roadmap checkmarks inside older planning docs.

**Legend — Runtime status**

| Token | Meaning |
| ----- | ------- |
| **implemented** | Code path exists; exercised when dependencies and env are configured. |
| **partial** | Code exists; behavior depends on env, optional deps, or has known gaps vs narrative. |
| **optional** | Present in fuller compose or code; not required for minimal API SaaS path. |
| **dead_path** | Client/factory exists; no verified call graph in production ingest path (may still be useful for agents/tools). |
| **doc_only** | Claimed in planning docs (e.g. Redis Streams bus) with **no** matching implementation in `src/`. |

**Legend — Deploy surfaces**

| Surface | Definition |
| ------- | ---------- |
| **deploy_prod** | `deploy/docker-compose.prod.yml` (Kafka, processor, OPA, Qdrant, Mongo, Postgres, Redis, API). |
| **root_compose** | Root `docker-compose.yml` (full lab stack: Grafana, Prometheus, etc.—not the same as deploy_prod). |
| **API without brokers** | API process up but Kafka unreachable / producer `None` → `/api/v1/ingest` returns **503** (code). |

---

## Matrix

| Subsystem | Purpose | Code path | Dev | Prod / deploy_prod | Required for core ingest story | Failure mode | Fallback |
| --------- | ------- | --------- | --- | ------------------ | ------------------------------ | ------------ | -------- |
| FastAPI ingress | HTTP API, JWT/API-key auth, routing | `src/main.py`, `src/api/*` | Local `uvicorn` | `Dockerfile.api` → `kirp-api` | Yes | Uncaught handler → 500 + log; many routes map errors to HTTPException | None generic—per route |
| Tenant context | Resolve `tenant_id` / `space_id` / `user_id` from JWT or skip-auth | `src/auth/tenant_context.py`, middleware in `src/main.py` | Same | Same | Yes | Missing user on ingest → **403** | N/A |
| Kafka broker | Durable log for `kirp-events` | Confluent images in compose; `src/core/integrations.py` (`get_kafka_producer` / `get_kafka_consumer`) | Root compose or deploy_prod | deploy_prod | Yes for **JWT `/api/v1/ingest`** publish path; **no** in minimal SaaS compose | Producer `None` or emit fails → **503** on `/api/v1/ingest` with run step `kafka_emitted` failed | API retries none; client must retry |
| Kafka consumer worker | At-least-once consume → pipeline | `src/workers/kafka_processor.py` (`python -m src.workers.kafka_processor`) | deploy_prod `kirp-agent-processor` | Same | Yes for async processing of published events | Poll/parse errors logged; processing failure → offset **not** committed → redelivery | In-process retry `MAX_RETRIES=2`; backoff sleep |
| Redis — idempotency | Processor dedup `idempotency:{key}` TTL 1h | `src/workers/kafka_processor.py` (`_check_idempotency`, `_mark_processed`), `get_redis_async` | When `REDIS_URL` reachable | Same | Strongly expected with processor; if Redis missing, checks no-op → **dedup weakened** | `get_redis_async` None → skip Redis idempotency | Mongo event-id / external_id paths still reduce dupes |
| Redis — run lifecycle | `tenant:{tenant_id}:{run_id}`, lookup key | `src/core/run_controller.py` | Same | Same | Expected for run steps; **in-memory** mirror always | Redis ping fails → backoff; `_redis_hard_disabled` after init failure → **memory only** (multi-instance unsafe) | Same process still updates steps in RAM |
| EventRegistry | Dispatch canonical events to handlers / pipeline | `src/core/event_registry.py`, `src/core/event_registry_handlers.py` | Same | Same | Yes on processor path | Handler exception → processor failure path | Kafka retry semantics |
| EventPipeline | Govern → Mongo → embed → Qdrant → schema/agents | `src/core/pipeline.py`, `src/core/pipeline_factory.py` | Same | Same | Yes when pipeline runs | Governance deny → **PermissionError**; RAG embed/upsert errors logged; **best-effort** vector write | Event can persist without vectors (see pipeline code) |
| MongoDB EventStore | Events, M3 memory collections, timelines | `src/core/event_store.py`, Motor/pymongo via `get_mongo_client` | Local or compose | deploy_prod `mongo` | Yes | Connection failure → lazy init warnings; `/health` **503** if store init throws | None |
| Qdrant RAG | Vectors + semantic search | `src/core/rag_engine.py`, env `QDRANT_URL` | compose service | deploy_prod `qdrant` | Yes for RAG quality; ask/query degrade if down | `get_rag_engine` raises → `/health` 503; `/api/v1/ask` returns friendly string if RAG init fails in handler | Ask path soft-fail message (see `main.py`) |
| PostgreSQL | Relational models, audit log rows, SaaS | `src/core/integrations.py` `get_postgres_engine`, models under `src/models/` | compose | deploy_prod `postgres` | Yes in prod env validation (`DATABASE_URL`, `REDIS_URL`) | Session None → audit skip; governance audit `log_audit` catches and logs | stdout audit line still emitted |
| OPA | Policy allow / ABAC overlay | `deploy/docker-compose.prod.yml` `opa` + `deploy/opa/policies`; `src/core/governance.py`; `src/auth/rbac.py` | When `OPA_URL` set | deploy_prod | Optional for API boot; **governance fail-closed** when enabled | `OPA_URL` unset → governance **fail-open** (`allowed=True`, reason `Governance disabled`); HTTP/network error → **allowed=False** | Deny writes at pipeline |
| GovernanceEngine | Wrap OPA + risk heuristics | `src/core/governance.py` | Same | Same | Partial without OPA (open) | See OPA row | — |
| Agent framework | Registered agents, triggers | `src/core/agent_framework.py`, `src/core/agent_registry.py` | Same | Same | Optional per event type | Agent errors bubble to processor retry | — |
| LLM providers | OpenAI / Anthropic / Ollama invocations | `src/core/llm_client.py` (httpx **60s** timeout) | Env keys | Same | Optional until agent/insight path used | Timeout / HTTP error → exception to caller | Caller-dependent (processor retries limited) |
| Stripe SaaS | Webhooks + PaymentIntent | `src/main.py`, `src/services/stripe_service.py` | Env keys | Same where configured | For billing only | Misconfig → **503** PaymentIntent; bad webhook sig → **400** | — |
| Webhooks Slack / WhatsApp / Notion | Ingest via Kafka | `src/api/v1_ingestion.py`, integrations under `src/integrations/` | Env tenant routing | Same | No for core if not used | **Kafka emit return ignored** → HTTP **200** with `ok: true` even if bus down (**legibility gap** vs `/api/v1/ingest`) | Operator must verify Kafka lag / processor |
| Prometheus metrics | Counters/histograms in pipeline/worker | `src/observability/metrics.py` | `DISABLE_PROMETHEUS=1` on processor in deploy_prod | Optional | No for correctness | Library missing → no-op metrics | — |
| Observability HTTP | `/observability/*`, `/health` | `src/api/observability.py`, `src/main.py` | Same | Same | Operational | `/health` hits Mongo+RAG—**not** Kafka | `/healthz` lightweight |
| Redis Streams event bus | Alternative bus | **doc_only** (`UNIFIED_ARCHITECTURE.md` mentions); **no** `EVENT_BUS_PROVIDER` or streams publisher in `src/` | N/A | N/A | Not implemented | N/A | Kafka only |
| Cassandra | Legacy integration hook | `get_cassandra_session` in `src/core/integrations.py` | Optional | Not in deploy_prod service list | **dead_path** for ingest | Import/driver failure → None | N/A |
| Elasticsearch | Metrics agent | `get_elasticsearch_client`, `src/agents/metrics_agent.py` | optional | Not wired in deploy_prod excerpt | **dead_path** for default deploy | Client None → agent sees no ES | N/A |
| Grafana / Prometheus stack | Dashboards | Root `docker-compose.yml` only | Lab | Not in `deploy/docker-compose.prod.yml` | optional | N/A | N/A |
| `publish_ingest_event` | Post-pipeline Kafka publish helper | `src/core/ingest_kafka.py` | — | — | **dead_path** (no callers in `src/` grep) | Raises on failure if ever called | Currently unused |
| CommandExecutor (diagram) | Side-effect execution | `src/agents/command_executor.py`, legacy `src/compat/legacy_agents.py` | partial | MetaAgent preferred per compat strings | Narrative box maps to **multiple** implementations | N/A | Trace via agent registry, not single class |

---

## Conflicts resolved (doc vs code)

1. **Event bus:** Code paths use **Kafka** (`confluent-kafka`). **Redis Streams bus is not implemented** in `src/` despite older unified-architecture prose (“Redis Streams (dev)”).
2. **`deploy/docker-compose.prod.yml` includes Kafka, Zookeeper, and `kirp-agent-processor`** (verified in repo). `deploy/README.md` still claims the “minimal” prod compose stack has **no Kafka** and that ingest returns 503 for that reason—that sentence is **stale/incorrect** relative to the compose file. **503 on `/api/v1/ingest`** still occurs whenever the **producer** cannot connect or `emit` fails (e.g. API-only process, wrong bootstrap host, missing `confluent-kafka`).
3. **Webhooks vs JWT ingest:** Only **`POST /api/v1/ingest`** treats missing Kafka as **503**. Webhook routes can report success without verifying Kafka publish—documented as a **behavior gap**.

---

## How to re-verify

```bash
rg -n "get_kafka_producer|KafkaEventAgent|GovernanceEngine|RunController|idempotency" src/
docker compose -f deploy/docker-compose.prod.yml config --services
./deploy/verify-ingest-e2e.sh
python3 -m pytest tests/ -q
```
