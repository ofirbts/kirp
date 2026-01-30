# KIRP Backend — Core Systems Implemented

This document lists the new backend modules, API endpoints, worker tasks, Kafka topics, event schemas, agent schemas, governance policies, and brand templates implemented for the seven core systems. The Next.js dashboard was **not** modified.

---

## 1. New Backend Modules

| Module | Path | Purpose |
|--------|------|---------|
| **EventPipeline** | `src/core/pipeline.py` | Ingest → Governance → Store (Mongo) → Embed → Qdrant. Optional `event_id` for Kafka re-ingest. |
| **Agent Engine** | `src/core/agent_engine.py` | Execution engine (async + Redis queue), state machine (idle→running→completed|failed), AgentMemory (Qdrant+Redis), SkillsRegistry, AgentOrchestrator, PersonaSpec, WorkflowStep. |
| **Event Store (extended)** | `src/core/event_store.py` | Event model: `correlation_id`, `parent_event_id`, `actor`, `version`. Methods: `replay()`, `move_to_dlq()`, `list_dlq()`, `retry_dlq()`, `delete_older_than()`. List supports `agent_id`, `correlation_id`. |
| **Governance Bundles** | `src/core/governance_bundles.py` | PolicyBundle, GovernanceEnforcement (check + audit in one call), multi-tenant isolation at hook level. |
| **Brand Engine** | `src/core/brand_engine.py` | BrandTemplate, BrandMemory, BrandEngine (templates, memory, render for email/WhatsApp/social). |
| **Realtime Gateway** | `src/api/realtime_ws.py` | WebSocket `/api/v1/realtime/ws` with subscribe/unsubscribe channels: `events`, `metrics`, `agents`, `audit`, `*`. ConnectionManager for broadcast. |

---

## 2. Updated API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| **Events** | | |
| GET | `/api/events` | List events (EventStore-backed; tenant/space/agent_id/correlation_id). |
| GET | `/api/events/dlq` | List DLQ events. |
| POST | `/api/events/{event_id}/replay` | Replay: returns payload for re-ingest. |
| POST | `/api/events/dlq/{event_id}/retry` | Returns DLQ payload for retry. |
| **Agents** | | |
| GET | `/api/agents` | List agents from AgentFramework (tenant-scoped). |
| GET | `/api/agents/{agent_id}` | Get single agent. |
| POST | `/api/agents/{agent_id}/run` | Enqueue agent run; returns `decisionId` (run_id) and status. |
| GET | `/api/agents/runs/{run_id}` | Get agent run status (idle/running/completed/failed), output, error. |
| **Realtime** | | |
| WebSocket | `/api/v1/realtime/ws` | Subscribe: `{"subscribe": "events"|"metrics"|"agents"|"audit"|"*"}`. |
| GET | `/api/v1/realtime/events/stream` | SSE placeholder for events. |
| **Existing** | | |
| GET | `/health` | Health check. |
| GET | `/api/v1/stats` | Dashboard stats. |
| POST | `/api/v1/ingest` | Ingest → pipeline. |
| POST | `/api/v1/query` | RAG query. |
| GET | `/api/v1/agents` | List registered agents (main.py). |
| Governance, observability, whatsapp, brand, command, auth | (unchanged prefixes) | |

---

## 3. Updated Worker Tasks

| Task | Queue | Description |
|------|-------|--------------|
| `ingest_task` | ingest | Ingest content via EventPipeline. |
| `refresh_missing_embeddings_task` | scheduled | Refresh embeddings in Qdrant (hourly). |
| `daily_intelligence_task` | scheduled | Daily intelligence (08:00). |
| `self_improvement_task` | scheduled | Self-improvement (02:00). |
| `demo_data_generator_task` | scheduled | Demo data. |
| **agent_run_task** | **agents** | Process one agent run (run_id, agent_name, tenant_id, …); execute via AgentFramework handler; set state in Redis. |
| **drain_agent_queue_task** | **agents** | Beat every 10s: pop one from Redis `agent_run_queue`, dispatch `agent_run_task`. |

---

## 4. Kafka Topics

| Topic | Purpose |
|-------|---------|
| `kirp-events` | Event stream; consumed by Kafka processor → EventPipeline (existing). |
| `kirp-agent-triggers` | (Optional) Event-driven agent triggers; can be consumed to enqueue runs to Redis `agent_run_queue`. |

---

## 5. Event Schemas (Event Store)

**Event** (Mongo + JSON payload):

- `id`, `tenant_id`, `space_id`, `user_id`, `source`, `content`, `metadata`, `embedding`, `timestamp`, `sensitivity`, `event_type`, `trace_id`
- **New:** `correlation_id`, `parent_event_id` (causality), `actor`, `version`

**DLQ:** Same document in `dlq_events` with `dlq_reason`, `dlq_at`.

---

## 6. Agent Schemas (Agent Engine)

- **AgentRun:** `run_id`, `agent_name`, `tenant_id`, `space_id`, `user_id`, `state`, `trigger`, `trigger_ref`, `input_context`, `output`, `error`, `started_at`, `finished_at`, `created_at`
- **AgentRunState:** `idle` | `running` | `completed` | `failed` | `cancelled`
- **SkillSpec:** `name`, `description`, `parameters_schema`, `handler`
- **WorkflowStep:** `step_id`, `agent_or_skill`, `input_map`, `condition`
- **PersonaSpec:** `system_prompt`, `few_shot_examples`, `temperature`, `max_tokens`

---

## 7. Governance Policies

- **OPA:** Existing `deploy/opa/policies/kirp.rego` (Rego v1 fixes applied).
- **GovernanceEnforcement:** `enforce(tenant_id, space_id, user_id, action, resource, …)` → OPA check + audit log. Multi-tenant: `tenant_id` required.

---

## 8. Brand Templates

- **BrandTemplate:** `id`, `tenant_id`, `name`, `channel` (email|whatsapp|linkedin|twitter), `subject_key`, `body_template`, `tone`, `variables`
- **BrandMemory:** `id`, `tenant_id`, `content`, `kind` (guideline|voice|example), `channel`
- **BrandEngine:** `get_template`, `list_templates`, `save_template`, `get_brand_memory`, `add_brand_memory`, `render(tenant_id, channel, template_name, variables)`

---

## 9. End-to-End Tests

- Run: `./TEST_E2E.sh`
- Pipeline: ingest → store → RAG; API health, OpenAPI, Kafka produce/consume (with extended timeout and `srvr` Zookeeper healthcheck).
- OPA: policy loads without parse errors.
- New capabilities: Event replay/DLQ and agent run enqueue/status are available via API; workers process agent queue when Celery beat and worker are running.

---

## 10. Summary

- **Agent Engine:** Execution (async + Redis queue), state machine, memory (Qdrant+Redis), skills registry, workflows, persona; API run + run status; worker `agent_run_task` + `drain_agent_queue_task`.
- **Event Store:** Append-only log, replay, DLQ (move/list/retry), partitioning (tenant, agent_id, correlation_id), retention (`delete_older_than`), causality (`parent_event_id`), correlation_id, metadata (actor, version).
- **RAG + Agents:** AgentMemory and AgentOrchestrator in agent_engine; RAG engine unchanged; full agent-driven RAG orchestration can be added on top.
- **WhatsApp Intelligence:** Existing daily_intelligence_task and whatsapp_os API; prioritization/aggregation can be added in services.
- **Governance:** Policy bundles (metadata), enforcement hooks (check + audit), multi-tenant isolation.
- **Brand OS:** BrandEngine with templates, memory, multi-channel render.
- **Real-time:** WebSocket gateway with channel subscribe (events, metrics, agents, audit); broadcast helper for pipeline/workers to push live updates.

No changes were made to the Next.js dashboard structure or routes.
