# Architecture traceability

Maps **diagram boxes and narrative layers** to **modules, interfaces, and maturity**. Pair with `docs/RUNTIME_REALITY_MATRIX.md` and `docs/FAILURE_SEMANTICS.md`.

## Executive brief Mermaid (`docs/KIRP_EXECUTIVE_TECHNICAL_BRIEF.md`)

| Diagram node | Implementation | Interfaces | Runtime deps | deploy_prod | Maturity | Tests (examples) |
| ------------ | ---------------- | ---------- | ------------ | ----------- | -------- | ---------------- |
| Client | Next.js app `app/`, `components/` | HTTPS to API | API URL | external | implemented | E2E docs under `docs/` |
| FastAPI | `src/main.py` + routers `src/api/` | OpenAPI / REST | Mongo, Redis, Postgres, optional Kafka/Qdrant/OPA | `kirp-api` | implemented | `tests/` API modules |
| Kafka `kirp-events` | `src/core/integrations.py`, `src/agents/kafka_event_agent.py` | Kafka protocol | Broker | `kafka` | implemented | ingest E2E script |
| Processor | `src/workers/kafka_processor.py` | consume `kirp-events` | Kafka, Mongo, Redis, Postgres, Qdrant, OPA (via pipeline) | `kirp-agent-processor` | implemented | processor unit tests if present |
| Redis idempotency | `kafka_processor` + `get_redis_async` | Redis GET/SETEX | Redis | `redis` | partial without Redis | — |
| EventRegistry | `src/core/event_registry.py`, handlers `src/core/event_registry_handlers.py` | `dispatch(CanonicalEvent)` | Mongo, pipeline | worker | implemented | registry tests |
| EventPipeline | `src/core/pipeline.py`, factory `src/core/pipeline_factory.py` | `run`, `run_post_ingest_for_event` | Store, RAG, schema, gov, agents | worker | partial (schema maturity per UNIFIED) | pipeline tests |
| OPA governance | `src/core/governance.py`, policies `deploy/opa/policies/` | HTTP `POST /v1/data/kirp/governance/allow` | OPA | `opa` | partial (fail-open if URL unset) | governance tests |
| Mongo | `src/core/event_store.py` | Motor/Mongo API | Mongo | `mongo` | implemented | many |
| Embed / Qdrant | `src/core/rag_engine.py` | qdrant-client / embeddings | Qdrant + provider keys | `qdrant` | implemented | RAG tests |
| Postgres schema | `src/core/schema_engine.py`, `src/models/schema.py` | SQLAlchemy | Postgres | `postgres` | partial per UNIFIED | — |
| Agents / ask | `src/core/agent_framework.py`, `src/agents/`, `InsightAgent` | registry + LLM | LLM, RAG | API | implemented | agent tests |
| RunController Redis | `src/core/run_controller.py` | Redis hashes | Redis | `redis` | partial (memory fallback) | run controller tests |
| CommandExecutor | `src/agents/command_executor.py`, legacy `src/compat/legacy_agents.py` | agent specs | varies | — | partial / legacy | grep-based trace |

## UNIFIED ASCII diagram (`UNIFIED_ARCHITECTURE.md`)

| Box | Trace | Notes |
| --- | ----- | ----- |
| API Layer `/ingest` | `main.py` `POST /api/v1/ingest`; legacy routes may exist | JWT ingest is canonical for bus publish + 503 semantics. |
| Event Pipeline 9 steps | `EventPipeline.run` + `kafka_processor` + registry | Step parity is **not** 1:1 with ASCII numbering; verify `pipeline.py` order. |
| Event Store (Mongo) | `EventStore` | |
| RAG Engine (Qdrant) | `RAGEngine` / `get_shared_rag_engine` | |
| Schema Engine (PG) | `schema_engine.py` | Maturity per UNIFIED §3.2.3 (often behind narrative). |
| Event Bus (Kafka) | `integrations.py` + `KafkaEventAgent` | Redis Streams alternative: **not implemented**. |
| Governance | `governance.py` | |
| Agent Framework | `agent_framework.py` | |

## Worker / sidecar boundaries

| Process | Entry | Must not |
| ------- | ----- | -------- |
| API | `uvicorn src.main:app` | Assume Kafka publish without checking `emit` return (webhooks—see FAILURE_SEMANTICS). |
| Processor | `python -m src.workers.kafka_processor` | Commit offset before successful `process_event`. |

## “No magic boxes” exceptions

- **Pluggable bus (Redis Streams):** documented historically; **only Kafka** in `src/`.
- **CommandExecutor in diagrams:** name maps to **legacy + MetaAgent** paths; trace via `register_all_agents` and `InsightAgent` usage, not one class.
