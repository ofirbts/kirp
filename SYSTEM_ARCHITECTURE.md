# KIRP — System Architecture (Current State)

Document purpose: precise definition of architecture, execution flows, and mental models. No marketing; engineering facts only. For senior engineer onboarding and audit.

**Operational truth (Redis run keys, pipeline vs `run_post_ingest_for_event`, cross-store failure order, idempotency, OPA deny behavior, metrics scrape paths, doc-linked regression test index):** see **`SYSTEM_STATUS.md`** in the repo root.

---

## 1. Core Concept

**KIRP is an Agent Orchestrator** that sits between users/integrations and multiple LLM providers, RAG, and governance.

- Events (ingest, M3 reflections, agent runs) enter via API or Kafka; a single **EventPipeline** runs: governance check → store event in Mongo → embed content → upsert to Qdrant → write history/timeline → extract life objects → upsert schema nodes in Postgres. No state change happens without an event. Tenant and user are carried on every path; OPA governs writes. Agents (Insight, Planner, M3 classifiers, etc.) are invoked from this pipeline or from explicit API calls, and they use RAG + LLM routing by task type (reasoning, bulk, ui, dev).

---

## 2. Execution Flow

End-to-end, step by step. Two main entry paths: **Ingest (async via Kafka)** and **Sync (API-only, e.g. /ask, /m3/reflect)**.

### Path A: Ingest (UI → API → Kafka → Processor → Pipeline)

| Step | What happens | Who | Result |
|------|--------------|-----|--------|
| 1 | User submits content (e.g. from Dashboard or Notion sync). | Next.js UI | HTTP POST to API. |
| 2 | Request hits FastAPI; auth middleware sets `request.state.user` (JWT or SKIP_AUTH dev user). | `src/main.py` (auth_middleware) | tenant_id, space_id, user_id available. |
| 3 | Route `POST /api/v1/ingest` or Notion/sync. Builds payload with tenant_id, space_id, user_id, content, source, metadata. | `src/main.py` (ingest) | No DB/LLM yet. |
| 4 | **KafkaEventAgent.emit()** serializes envelope (type=`ingest`, payload) to topic `kirp-events`. | `src/agents/kafka_event_agent.py` | Event queued; API returns 200. |
| 5 | **Kafka processor** (separate process) consumes message. Optional **Redis idempotency** check (`idempotency:{key}`); if already processed, skip. | `src/workers/kafka_processor.py` | Dedup; then build CanonicalEvent. |
| 6 | **EventRegistry.dispatch(canonical)**. event_type = `ingest` → handler **handle_ingest_v1**. | `src/core/event_registry.py`, `event_registry_handlers.py` | Handler resolves. |
| 7 | **EventPipeline.run()** (governance → store → embed → Qdrant → history → schema). | `src/core/pipeline.py` | See Path A detail below. |
| 8 | After pipeline: **Redis idempotency** key set (TTL 1h). | `kafka_processor` | Prevents duplicate processing. |

**Path A detail — inside EventPipeline.run():**

| Step | What | Component | DB/Provider |
|------|------|-----------|-------------|
| A1 | Build governance context (sensitivity, event_type; for M3: identity_entropy_score, resource_type). | pipeline | - |
| A2 | **GovernanceEngine.check()** (OPA HTTP). allowed / requires_approval; if M3 and requires_approval → optional WhatsApp escalation. | `src/core/governance.py` | OPA (HTTP) |
| A3 | Create Event in memory; **RAGEngine.embed(content)**. | pipeline, `rag_engine` | **OpenAI** (or EMBEDDING_PROVIDER) |
| A4 | **RAGEngine.upsert()** one point (id=event_id, embedding, payload with tenant_id, space_id, user_id, event_type, etc.). | `rag_engine` | **Qdrant** |
| A5 | **EventStore.ingest(event)**. | `event_store` | **MongoDB** (events collection) |
| A6 | **record_history()** — human-readable timeline entry. | `src/core/history.py` | **MongoDB** (history collection) |
| A7 | **extract_life_objects()** + **SchemaEngine.upsert_node()** per entity (task, commitment, etc.). | `life_objects`, `schema_engine` | **Postgres** (schema_nodes, life_areas) |

### Path B: Sync request (e.g. /ask or /m3/reflect)

**Example: POST /api/v1/ask**

| Step | What | Who | DB/Provider |
|------|------|-----|-------------|
| 1 | Request + JWT → auth → get_current_user. | main.py | - |
| 2 | **get_rag_engine()** (lazy init RAGEngine: Qdrant + embedder). | main | Qdrant, OpenAI (embed) |
| 3 | **InsightAgent(rag).ask(tenant_id, space_id, query, user_id)**. | `src/agents/insight.py` | - |
| 4 | **RAGEngine.search(query, tenant_id, space_id, user_id)** → embed query, query_points on Qdrant (filter tenant_id, space_id, user_id), optional BM25; hybrid rank. | `rag_engine` | **Qdrant**, **OpenAI** (embed) |
| 5 | **get_llm_for_task("reasoning")** → LLMClient(provider, model) from env (e.g. REASONING_PROVIDER=groq). | `llm_router` | Config only |
| 6 | **LLMClient.invoke()** with system prompt + context snippets. | `llm_client` | **Groq/OpenAI/Gemini/Anthropic** (per router) |
| 7 | Return answer + sources to API → JSON to UI. | main | - |

**Example: POST /api/v1/m3/reflect**

| Step | What | Who | DB/Provider |
|------|------|-----|-------------|
| 1 | Body + TenantContext (JWT). Optional **Idempotency-Key**: if present, **get_m3_memory_store().get_idempotency_event_id()**; if found → return 200 with same event_id. | v1_m3 | **Mongo** (m3_idempotency) or in-memory |
| 2 | Build **CanonicalEvent** (event_type=EVENT_M3_DAILY_REFLECTION_SUBMITTED, source=m3_reflect, content=reflection_text, metadata). | v1_m3 | - |
| 3 | **get_event_registry().dispatch(event)** → **handle_m3_event** (M3 handler). | event_registry, m3/handlers | - |
| 4 | **_get_pipeline()** (same as ingest: EventStore, RAGEngine, SchemaEngine, Governance, AgentFramework). | m3/handlers | - |
| 5 | **pipe.run(..., event_type=m3.daily_reflection_submitted)** → governance (OPA, optional M3 WhatsApp) → embed → Qdrant upsert → **EventStore.ingest** → record_history → life_objects + schema. | pipeline | OPA, **OpenAI** embed, **Qdrant**, **Mongo**, **Postgres** |
| 6 | **m3_memory_writeback()** → append_reflection to M3 memory (in-memory or Mongo M3 collections). | m3/writeback | **M3 memory** (Mongo or in-memory) |
| 7 | **run_m3_stages()** → context from M3 memory, then **ReflectionClassifierAgent** (LLM), **GapAnalysisAgent**, **MicroActionGeneratorAgent**, **IdentityDiscriminatorAgent**; classifier result → **update_last_reflection_classification**; gap result → **append_gap_snapshot**; micro actions → **upsert_micro_action**. | m3/stages, m3/agents | **get_llm_for_task("bulk")** (e.g. Groq), **M3 memory** |
| 8 | If idempotency_key was sent, **record_idempotency(..., event_id)**. | v1_m3 | M3 memory |
| 9 | Return 201 { ok, event_id }. | v1_m3 | - |

### Provider selection (LLM)

- **llm_router.get_llm_for_task(task_type)** returns an **LLMClient**.
- task_type ∈ { critical, reasoning, bulk, ui, dev }. Default mapping: critical→OpenAI, reasoning→Anthropic (or REASONING_PROVIDER env), bulk→Groq, ui→Gemini, dev→Ollama.
- Env overrides: e.g. `REASONING_PROVIDER=groq` → Groq client. No runtime metrics; selection is by config/env only.

### Summary table: who writes where

| Data | Written by | Storage |
|------|------------|---------|
| Raw events | EventPipeline.run() → EventStore.ingest() | MongoDB (events) |
| Vectors | EventPipeline → RAGEngine.upsert() | Qdrant |
| History entries | Pipeline → record_history() | MongoDB (history) |
| Schema nodes / life areas | Pipeline → SchemaEngine.upsert_node(), ensure_life_areas | Postgres |
| Agent run logs | AgentScheduler.run_agent_and_log → AgentLogsStore.append | MongoDB (agent_logs) |
| Agent actions (pending/executed) | run_agent_v1, ExecutionAgent, etc. → AgentActionsStore | MongoDB (agent_actions) |
| M3 reflections, actions, syntheses, evolutions, idempotency, gap_snapshots | M3 writeback + stages | M3 memory (in-memory or MongoDB m3_* collections) |
| Idempotency (Kafka) | kafka_processor _mark_processed | Redis (idempotency:* TTL 1h) |
| RAG cache (optional) | cache.get_cached / set_cached | Redis (cache:*) |
| Schema list cache | SchemaEngine list_nodes (use_cache=True) | Redis |

---

## 3. State Model

| State | Where stored | Scope | Notes |
|-------|--------------|-------|-------|
| **Conversation state** | Not a single store. Per-request; agent runs store results in agent_actions / agent_logs. M3 “conversation” is reflection list + synthesis/evolution in M3 memory. | tenant, user | No global “session” object; history + M3 memory form timeline. |
| **Memory** | **Operational**: MongoDB (events, history, agent_logs, agent_actions). **Semantic**: Qdrant (vectors + payload). **M3-specific**: M3 memory (in-memory or Mongo m3_reflections, m3_micro_actions, etc.). **Short-term/cache**: Redis (idempotency, schema cache, RAG cache). | tenant_id, space_id, user_id on all | AgentEngine/BrandEngine use Redis for short-term session memory when present. |
| **Vector memory** | Qdrant. One collection (e.g. kirp_vectors); payload includes tenant_id, space_id, user_id, event_type, event_id, content, source. M3 points also have module=m3. | tenant, space, user in filter | RAG search always filters by tenant_id (and optionally space_id, user_id). |
| **Tenant info** | Postgres (tenants/spaces tables via schema or auth); JWT carries tenant_id, space_id, user_id. No single “tenant store” in this doc. | - | Enforced at API layer (get_tenant_context) and in pipeline/metadata. |
| **Tool history** | Agent “tools” are internal (e.g. SchemaEngine, RAG). ExecutionAgent consumes AgentActionsStore (pending actions). Action outcomes stored as status in agent_actions. No separate “tool call log” table. | tenant, user | Tool history = agent_actions documents + agent_logs. |

---

## 4. Failure Map

**Qdrant down**

- **User impact**: Ingest: embed + upsert to Qdrant fails (logged); event is still written to Mongo. So new content is stored but not searchable until Qdrant is back and/or re-indexed. RAG search (/query, /ask, InsightAgent) fails → 500 or empty context. M3 reflect: same — event and M3 writeback can succeed, but pipeline’s Qdrant upsert fails (best-effort).
- **Fallback**: None. RAG and pipeline assume Qdrant is available for new writes; reads fail without it.
- **Recovery**: Restore Qdrant; optionally replay events from Mongo to re-embed and re-upsert (run_post_ingest_for_event or batch re-embed).

**OpenAI (or configured LLM/embedding provider) down**

- **User impact**: Embedding calls fail → pipeline’s embed step fails (warning logged; event still stored in Mongo without vector). RAG search may use cached or existing vectors only; new content has no vector. If InsightAgent or M3 agents call LLM and that provider is down → request fails (500 or error from agent).
- **Fallback**: No automatic provider failover for a single request. Different task types use different providers (reasoning vs bulk); so one provider down affects only that task type.
- **Recovery**: Fix provider or switch env (e.g. EMBEDDING_PROVIDER, REASONING_PROVIDER) and restart.

**Kafka down**

- **User impact**: **Ingest**: KafkaEventAgent.emit() fails → API returns 503 “Event bus unavailable”; no event is stored. All ingest paths that go through Kafka (e.g. POST /api/v1/ingest, Notion sync that enqueues) fail. **Consumption**: If processor is down or Kafka is down, events already in the topic are not processed until Kafka and processor are back.
- **Fallback**: None. Ingest is designed to be async via Kafka; no sync fallback in main ingest route.
- **Recovery**: Restore Kafka; processor reconnects and continues consuming. No DLQ in code; failed messages stay in topic or are retried by processor (MAX_RETRIES with backoff).

**Redis down**

- **User impact**: **Kafka idempotency**: _check_idempotency / _mark_processed fail (logged); idempotency is skipped → risk of duplicate processing of the same event. **Schema cache**: list_nodes cache misses; more Postgres reads. **RAG cache**: cache misses. **Agent engine**: If AgentExecutionEngine or AgentMemory use Redis, agent queue and short-term memory fail (agents that depend on Redis for state/queue see errors).
- **Fallback**: Code often checks “if redis” and continues without cache/idempotency; so many paths degrade but do not hard-fail. Ingest can still be processed without idempotency.
- **Recovery**: Restore Redis; idempotency and caches start working again. No automatic replay of “maybe duplicated” events.

**MongoDB down**

- **User impact**: Event store, history, agent_logs, agent_actions all fail. Pipeline cannot ingest; /ask does not depend on Mongo directly but history and events do. M3 memory (if backend=mongo) fails → M3 reflect/list fail.
- **Fallback**: None.
- **Recovery**: Restore Mongo; resume operations.

**Postgres down**

- **User impact**: SchemaEngine (life areas, nodes) fails → pipeline’s life-object extraction and upsert_node fail (logged; event and vector and history may already be written). Tasks/nodes APIs and anything reading from schema fail.
- **Fallback**: None.
- **Recovery**: Restore Postgres; subsequent ingests will write schema again.

**OPA down**

- **User impact**: GovernanceEngine.check() fails (HTTP to OPA). If OPA is unreachable, behavior depends on implementation: often a failed check is treated as deny or as “allow with warning”. Pipeline may raise or proceed; need to check governance code for exact behavior. Typically one failed check fails the whole pipeline run.
- **Fallback**: Optional “governance disabled” when OPA URL is not set; when set and OPA is down, requests that need the check can fail.
- **Recovery**: Restore OPA; governance works again.

---

## 5. Mental Model Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ INTERFACE LAYER                                                              │
│  Next.js UI (3100)  │  FastAPI (8000)  │  Webhooks (Notion, WhatsApp, etc.) │
│  Auth: JWT or SKIP_AUTH → request.state.user (tenant_id, space_id, user_id)  │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ CORE ENGINE                                                                  │
│  • EventRegistry: event_type → handler (ingest.v1, agent_run.v1, m3.*)       │
│  • EventPipeline: governance → store → embed → Qdrant → history → schema     │
│  • Kafka processor: consume → idempotency (Redis) → dispatch → pipeline      │
│  • Agent run: AgentScheduler + handler → AgentFramework (spec.handler)     │
└─────────────────────────────────────────────────────────────────────────────┘
         │                    │                    │                    │
         ▼                    ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────┐    ┌──────────────────┐
│ MEMORY LAYER │    │ TOOL / DATA LAYER │    │ GOVERNANCE   │    │ EXTERNAL PROVIDERS│
│              │    │                  │    │              │    │                  │
│ • EventStore │    │ • SchemaEngine    │    │ • OPA        │    │ • OpenAI         │
│   (Mongo)    │    │   (Postgres)     │    │   (HTTP)     │    │ • Groq           │
│ • HistoryStore│   │ • RAGEngine      │    │ • M3 EGE     │    │ • Gemini API     │
│   (Mongo)    │    │   (Qdrant+embed)  │    │   (score)    │    │ • Anthropic      │
│ • M3 memory  │    │ • AgentActions   │    │ • M3 WhatsApp│    │ • Ollama         │
│   (mem/Mongo)│    │   AgentLogs      │    │   (escalate)│    │ • Embed: OpenAI  │
│ • Redis      │    │   (Mongo)        │    │              │    │   (or provider)  │
│   (cache,    │    │ • Life objects  │    │              │    │                  │
│   idempotency)│   │   extraction     │    │              │    │                  │
└──────────────┘    └──────────────────┘    └──────────────┘    └──────────────────┘
```

- **Core engine**: Single pipeline + registry; one place that orchestrates governance, store, RAG, history, schema. Kafka is the async entry for ingest; sync API calls dispatch directly.
- **Memory layer**: Where state lives (events, history, M3, cache, idempotency). No single “conversation store”; composed from events + history + M3 + Redis.
- **Tool layer**: Schema (nodes, life areas), RAG (search/upsert), agent actions/logs. “Tools” used by agents are these stores + LLM.
- **Governance layer**: OPA for policy; M3 EGE for identity score; M3 WhatsApp for human escalation when required.
- **External providers**: All LLM and embedding calls go through LLMClient and RAGEngine; provider chosen by task type and env.

---

## 6. Hidden Complexity Report

**Looks simple but fragile**

- **Single RAG collection**: One Qdrant collection for all events and M3; filter by tenant_id/space_id/user_id. Mis-filter or bug in filter → cross-tenant leak risk. No separate “RAG service”; RAG is in-process and shared.
- **Pipeline order**: Governance → embed → Qdrant → Mongo. If Mongo write fails after Qdrant upsert, you have a vector without canonical event (inconsistent). No two-phase commit.
- **M3 in-process**: M3 reflect runs full pipeline + writeback + stages in one request. Long-running; one slow LLM call blocks the HTTP response. No queue for M3 by default.
- **Agent logs/actions**: Stored in Mongo with tenant_id but no separate isolation layer; any bug in filter could expose cross-tenant. No rate limit or quota per tenant.

**Tightly coupled**

- **Pipeline and RAG**: Pipeline directly calls rag.embed() and rag.upsert(); no abstraction. Same process, same process lifecycle.
- **Pipeline and Schema**: Direct call to SchemaEngine.upsert_node() and ensure_life_areas. Postgres schema is coupled to pipeline’s life_objects output.
- **EventRegistry and handlers**: Handlers (handle_ingest_v1, handle_m3_event) each build their own pipeline instance (_get_pipeline) with hardcoded env (MONGO_URI, QDRANT_URL, etc.). Duplicated init logic; not a single shared pipeline singleton from main.
- **Kafka processor and EventRegistry**: Processor builds CanonicalEvent and dispatches; event_type comes from payload. If a new event type is added, both registry and processor (or API) must agree.

**Redundant or duplicated**

- **Pipeline construction**: event_registry_handlers._get_pipeline() and m3/handlers._get_pipeline() and kafka_processor inline EventStore/RAG/schema/gov/af — same components, multiple places. Config (URIs, provider) repeated.
- **History vs events**: Events are raw; history is human-readable timeline. Both in Mongo; different collections. Redundant for “what happened” but different granularity.
- **Idempotency**: M3 has its own idempotency (M3 memory); Kafka has Redis idempotency. Two mechanisms, no shared contract.

---

## 7. Founder Briefing (2 minutes)

**What KIRP is**

KIRP is an event-driven agent orchestration backend. Users and integrations send in content (ingest) or commands (ask, M3 reflect). Every change is an event: we check policy (OPA), store the event in Mongo, turn content into vectors in Qdrant, and derive structured data (tasks, commitments) in Postgres. We don’t mutate state without an event.

**Two main flows**

- **Ingest**: Content is published to Kafka. A worker consumes it, deduplicates with Redis, then runs the pipeline: governance → embed (OpenAI or configured provider) → write to Qdrant and Mongo → write a human-readable history line → extract “life objects” (tasks, etc.) and write to Postgres. So one event drives: search index (Qdrant), audit trail (Mongo), timeline (history), and graph (schema).
- **Ask / M3**: Synchronous. For “ask”, we run RAG search (Qdrant + optional BM25), then call an LLM (provider chosen by task type: reasoning, bulk, ui, dev). For M3 reflect, we run the same pipeline (governance, store, embed, Qdrant, Mongo, history, schema) plus M3-specific memory and agents (classifier, gap, micro-actions) and write everything into M3 memory (in-memory or Mongo).

**What depends on what**

- **Qdrant**: Search and “semantic memory”; if it’s down, search and new vector writes fail; events can still be stored in Mongo.
- **Kafka**: Ingest flow; if it’s down, you can’t enqueue new ingest; the worker can’t process.
- **Redis**: Idempotency for Kafka (avoid duplicate processing) and caching (schema, RAG). If down, we lose idempotency and cache; core ingest can still run with duplicate risk.
- **OpenAI (or embed/LLM provider)**: Embeddings and LLM calls; if down, embedding and any agent that uses that provider fail.

**Multi-tenancy**

- tenant_id, space_id, user_id come from JWT (or dev default). They’re passed through API, pipeline, and stores. Isolation is by filter in queries and in payload (e.g. Qdrant payload, Mongo queries). There is no per-tenant DB or per-tenant process; it’s logical isolation in shared stores.

---

## 8. M3 Reality Check

**1. Long context vs RAG**

- **Current**: RAG is used for general ingest (events in Qdrant) and for M3 only in the sense that pipeline writes M3 reflection content to Qdrant with `module=m3` for semantic search. M3 “memory” is the dedicated M3 store (reflections, actions, syntheses, evolutions), not long-context LLM.
- **Gap**: No use of 1M-token long context or context caching. RAG is still chunk/embed/retrieve. For M3, a long-context model could reduce reliance on separate RAG for “past reflections” if we fed them in-context; today we don’t. So RAG is still relevant for cross-event search; long-context could simplify some M3 flows but is not implemented.

**2. Tool calling and orchestrator complexity**

- **Current**: M3 stages call agents (ReflectionClassifier, GapAnalysis, MicroActionGenerator, Discriminator) in sequence; each agent has a handler that may call get_llm_for_task and parse JSON from the model. There is no single “Gemini tool-calling” loop; we have custom prompts and response parsing.
- **Gap**: Orchestrator is “medium” complexity: fixed stage order, no generic tool registry that the model calls. Newer models with native tool calling could replace some of the hand-written “call this agent then that” with one model call that chooses tools. Not done today; would simplify maintenance and add flexibility.

**3. Multi-provider routing**

- **Current**: Routing is by **task type** (critical, reasoning, bulk, ui, dev) and **env overrides** (REASONING_PROVIDER, BULK_PROVIDER, etc.). No runtime metrics: no latency-based, cost-based, or availability-based selection. Provider choice is static per deploy.
- **Gap**: No metrics (latency, cost, error rate) per provider or per tenant. Routing is configuration-only; no automatic failover or “cheapest available” logic. Acceptable for current scale; becomes a gap when scaling or when multiple tenants share the same process.

---

## 9. Dependency Map (Quick Reference)

| Dependency | Used by | If down |
|------------|---------|---------|
| **Redis** | Kafka idempotency, schema cache, RAG cache, optional agent queue/memory | Duplicate processing risk; slower reads; no cache. |
| **Qdrant** | Pipeline (embed+upsert), RAG search, /query, /ask, M3 semantic search | No vector write; no search; 500 or empty context. |
| **Kafka** | Ingest path (emit + consume) | Ingest API 503; no processing of queued events. |
| **OpenAI (or embed provider)** | RAGEngine.embed(), pipeline | No new vectors; pipeline logs warning, event still in Mongo. |
| **MongoDB** | Events, history, agent_logs, agent_actions, M3 (if backend=mongo) | No ingest persistence; no history; M3 fails if Mongo M3. |
| **Postgres** | SchemaEngine (nodes, life areas) | No schema updates; task/graph APIs fail. |
| **OPA** | GovernanceEngine.check() | Depends on implementation; often request fails or governance disabled. |

---

*End of SYSTEM_ARCHITECTURE.md. No improvements or redesign; current state only.*
