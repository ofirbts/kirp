# Stage 1 – Diagnosis
## KIRP OS – Complete Codebase Scan & Analysis

**Date:** 2025-01-25  
**Scope:** Full repository scan. No code changes.  
**Principles:** Simplicity > Cleverness | Stability > Features | Clarity > Complexity

---

## 1. What the System Does in Practice

### 1.1 Intended Purpose (from README & SYSTEM_CONTRACT)

- **KIRP OS** is an *agentic operating system* for controlled autonomous AI: event-driven orchestration, long-term memory (RAG), human-in-the-loop governance, self-improving agents, and enterprise integrations (WhatsApp, Notion, etc.).
- **Invariants:** No state mutation without event; agent state reconstructable; decisions explainable.
- **Capabilities:** Replayable sessions, policy-guarded autonomy, multi-tier memory, long-term knowledge.

### 1.2 Actual Behavior Today

- **API (FastAPI):** Exposes `/auth`, `/query`, `/ingest`, `/health`, `/agents`, `/insights`, `/streams`, `/webhooks/whatsapp`, `/webhooks/twilio`, `/jobs`, `/improvements`, `/self-improving`, `/sources`, `/protected`, plus **inline** `/dashboard/summary/{user_id}` and `/agent/query` on `app` (not via routers).
- **Query flow:** Authenticated `/query` → OmniAgent (LLM + RAG + Persistence). **Main’s `/agent/query`** is a **stub** that returns `"KIRP processed: {text[:50]}..."` and **never touches the real agent**.
- **Ingest flow:** Authenticated `/ingest` → `pipeline.ingest_text` (intent classification, chunking, vector store, events). Batch ingest exists but is **broken** (wrong `add_texts` usage).
- **Worker:** Redis-based consumer; handles `ingest_request` and `whatsapp_msg` (ingest + WhatsApp send). **Imports `MetricsCollector` from `app.core.metrics`**, but that module defines **`Metrics`** only; **`MetricsCollector`** lives in **`app.core.monitoring`** → **import error** at worker startup.
- **UI (Streamlit):** Calls `GET /api/v1/stats` and `GET /dashboard/summary/{user_id}`. **`/api/v1/stats` does not exist**; main only has `/dashboard/summary/{user_id}` (hardcoded fake metrics, **no auth**).
- **Dashboard:** `app.api.dashboard` implements real metrics via `PersistenceManager.get_dashboard_metrics`, but **the dashboard router is never mounted** in `main.py`. The only dashboard endpoint is main’s **fake** `/dashboard/summary/{user_id}`.

---

## 2. Current Architecture & Module Relationships

### 2.1 High-Level Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  FastAPI (main.py)                                                       │
│  Routers: auth, query, ingest, health, agents, insights, streams,       │
│           jobs, improvements, self_improving, sources, protected,        │
│           webhooks_whatsapp, webhooks_twilio                             │
│  Inline:  /dashboard/summary (fake), /agent/query (stub)                 │
└─────────────────────────────────────────────────────────────────────────┘
         │                    │                      │
         ▼                    ▼                      ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐
│  Agent          │  │  RAG            │  │  Persistence / Events        │
│  agent.py       │  │  vector_store   │  │  PersistenceManager (Mongo)  │
│  core_agent.py  │  │  qdrant_store   │  │  event_bus (Redis)           │
│  executor       │  │  sharded_store  │  │  events.py (PersistenceManager)│
│  multi_agent    │  │  retriever      │  └─────────────────────────────┘
│  planner, etc.  │  │  rag_engine     │
└─────────────────┘  │  retrieval_*    │
         │            └─────────────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐
│  LLM            │  │  Integrations   │  │  Redis                       │
│  client.py      │  │  notion         │  │  redis_client (async)        │
│  (Ollama)       │  │  whatsapp_*     │  │  integrations.redis (sync)   │
│  get_llm ❌     │  │  google_calendar │  │  redis_layer (sync)          │
└─────────────────┘  └─────────────────┘  │  worker (own connection)     │
                                          └─────────────────────────────┘
```

### 2.2 Config & Environment

- **`app.config.settings`:** Pydantic Settings (`openai_api_key`, `mongodb_uri`, `redis_url`). **Never imported** by the rest of the app → dead.
- **`app.core.config`:** Streamlit + `os.getenv` (MONGO_URI, NOTION_*, QDRANT_*, REDIS_*). **Imports `streamlit`** → unsuitable for API/worker.
- **Actual config:** `os.getenv` scattered across persistence, vector_store, worker, redis_client, integrations, etc. **No single source of truth.**

### 2.3 Data & Storage

- **MongoDB (Motor):** `PersistenceManager` — events, agent_states, improvements, jobs, users, sources. **Single async Mongo usage.**
- **Qdrant:** Three abstractions:
  - **`vector_store`** (LangChain `QdrantVectorStore` + OpenAI embeddings): used by agent, pipeline, retriever, status. **Primary**.
  - **`qdrant_store`** (raw `QdrantClient`): **only used by `sharded_store`**.
  - **`sharded_store`:** Thin wrapper over `qdrant_store`. **`get_sharded_store` unused** anywhere → dead.
- **Redis:** Four separate usages:
  - **`redis_client.get_redis`** (async): event_bus, health, status, monitoring. **event_bus** uses it **without `await`** and **sync-style `rpush`** → broken; **unused** (no `publish_event` callers).
  - **`integrations.redis_client`** (sync): metrics, MetricsCollector flush. **Worker** uses **`MetricsCollector`** from **`metrics`** (wrong module) → see below.
  - **`redis_layer`** (sync): simple get/setex. **Unused** → dead.
  - **Worker:** Own `redis.from_url(REDIS_URL)` async connection. Queue names: `kirp_events`, `kirp_events:high`, `kirp_events:low`.

### 2.4 Agent & RAG

- **Agents:**
  - **`agent.py`:** `OmniAgent` (conversational + RAG + persistence), **`CoreAgent`** (Notion sync loop). Exports **`agent`** (OmniAgent), **`system_agent`** (CoreAgent). **No `get_agent`**.
  - **`core_agent.py`:** **Different `CoreAgent`** (improvements/Notion loop), plus `ScraperAgent`, `KafkaEventAgent`. Exports **`agent`** (CoreAgent). **Naming and responsibility overlap** with `agent.py`.
  - **`executor.py`:** `ExecutorAgent` – **calls `PersistenceManager.get_user_events` without `await`** (async API used synchronously) → bug.
- **LLM:** `app.llm.client` has `LLMClient` and `ollama_client`. **`get_llm` is never defined.** Agent, rag_engine, self_improving_agent, intelligence_engine, monitoring all **`from app.llm.client import get_llm`** → **ImportError**.
- **RAG:** `rag_engine` → `retriever` → `search_vectors` (vector_store) + `retrieval_pipeline`. **OmniAgent** uses **vector_store** directly (simple similarity_search), **not** rag_engine. **Two parallel RAG paths** (agent vs. rag_engine/query_stream/insights/self_improving).

### 2.5 Auth & Security

- **`app.api.auth`:** JWT + login/register, **`get_current_user`** (returns `username`, `role`). Used by most API routes.
- **`app.core.security`:** **Different `get_current_user`** (returns raw JWT payload). **Only `protected`** uses it. **Two incompatible auth helpers.**
- **Health:** Uses `Depends(lambda: {"username": "system"})` → **no real auth** on `/health`.
- **Auth backdoor:** `verify_user` accepts `ofir` / `admin123` and returns admin **without DB check**.

---

## 3. Fragile Points, Duplication, Anti-Patterns, Technical Debt

### 3.1 Critical Bugs (Runtime / Import Failures)

| Location | Issue | Impact |
|----------|--------|--------|
| `app.llm.client` | **`get_llm` undefined** | Agent, rag_engine, self_improving, intelligence_engine, monitoring **fail on import or first use** |
| `app.core.metrics` | **`MetricsCollector` missing** (lives in `monitoring`) | **Worker, pipeline** fail on **`from app.core.metrics import MetricsCollector`** |
| `app.api.webhooks_whatsapp` | **`from app.agent.agent import get_agent`** | **`get_agent` does not exist** → ImportError on webhook load |
| `app.core.monitoring` | **`await get_vector_store()`** | `get_vector_store` is **sync**; cannot await → TypeError |
| `app.core.monitoring` | **`timing` method body not indented** | `self._counters[...]` at module level → IndentationError / wrong behavior |
| `app.core.event_bus` | **`redis = get_redis()`** (no await), **`redis.rpush`** (async client) | Broken; **unused** anyway |
| `app.agent.executor` | **`PersistenceManager.get_user_events`** used without **`await`** | Async API called synchronously → invalid |
| `app.core.intelligence_engine` | **`search_vectors(...)`** not awaited; **signature** uses `user_id` | Wrong usage + missing await |
| `app.core.intelligence_engine` | **`PersistenceManager.save_insight`** | **Method does not exist** on PersistenceManager |
| `app.api.ingest_batch` | **`add_texts(all_chunks)`** | `add_texts_with_metadata` expects **(texts, user_id, metadatas)** → wrong signature, **no user_id** |
| `app.rag.rag_engine` | **`llm.ainvoke`** and **`res.content`** | `LLMClient` has **`ask`** returning **str**; no `ainvoke` / `.content` → **interface mismatch** |

### 3.2 Duplication & Overlap

- **Config:** `app.config.settings`, `app.core.config`, and ad-hoc `os.getenv` everywhere.
- **Redis:** Four different clients (redis_client async, integrations sync, redis_layer sync, worker own).
- **Mongo:** PersistenceManager (Motor, async) vs. `integrations.get_mongo_db_instance` (sync). **Sync Mongo unused** in practice.
- **Vector store:** `vector_store` (primary), `qdrant_store`, `sharded_store` (latter two largely unused).
- **Agents:** Two `CoreAgent` implementations (`agent.py` vs. `core_agent.py`); two `agent` exports; **ExecutorAgent** overlaps with **CoreAgent** (Notion/improvements).
- **Auth:** Two `get_current_user` implementations (auth vs. security).
- **Event semantics:** **MongoDB events** (PersistenceManager) vs. **Redis event queue** (event_bus, worker). **No single event model.**

### 3.3 Anti-Patterns & Structural Issues

- **Stub routes in main:** `/agent/query` and `/dashboard/summary` are **inline** stubs; **dashboard router** (real implementation) **never mounted**.
- **Status API:** **Never mounted**; `status` router unused. UI / tools that expect it get 404.
- **Hardcoded dashboard:** Main’s `/dashboard/summary` returns **literal** `knowledge_items: 1234`, `active_jobs: 5`, etc., **no DB**.
- **Health auth bypass:** Fake `Depends(lambda: ...)` instead of real JWT.
- **Scattered env:** No central config; **MONGO_URI** vs **mongodb_uri**, **REDIS_URL** vs **redis_url** vs **REDIS_HOST**/PORT, **QDRANT_HOST** vs **QDRANT_URL**.
- **PersistenceManager** `asyncio.create_task(initialize())` at module load → **implicit lifecycle**; also **explicit** init in main lifespan.

### 3.4 Technical Debt

- **`requirements.txt`:** Uses **`langchain_text_splitters`** in code (**chunker**) but **not listed** in requirements → **missing dependency**. **`aioredis`** present while **`redis`** async is used → redundant / confusion.
- **`config/settings`** uses **`pydantic_settings`**; **not in requirements**.
- **Streamlit in core config:** `app.core.config` imports **`streamlit`** → **tight coupling** of backend config to UI.
- **Notion:** Both **shared `notion`** (from `app.services.notion`) and **direct `NotionClient()`** in agent/core_agent → **inconsistent** usage.
- **Worker job status:** Persists **events** (e.g. `job_status_update`) but **never** uses **`PersistenceManager` jobs API** (`create_job`, `update_job`, `get_job`).

---

## 4. Redundant or Risky Files / Services

### 4.1 Effectively Dead or Broken

- **`app.config.settings`** – Unused.
- **`app.core.redis_layer`** – Unused.
- **`app.rag.sharded_store`** / **`get_sharded_store`** – Unused.
- **`app.rag.qdrant_store`** – Only used by sharded_store; **could be removed** if sharded_store goes.
- **`app.core.event_bus`** – Broken (async misuse); **`publish_event`** has **no callers**.
- **`app.api.dashboard`** – **Router never mounted**; real dashboard logic unused.
- **`app.api.status`** – **Router never mounted**; status API unused.
- **Main’s `/agent/query`** – Stub only; **diverts** from real agent flow.
- **Main’s `/dashboard/summary`** – Fake data; **overrides** intent of dashboard module.

### 4.2 Risky or Inconsistent

- **`app.core.integrations`** – Instantiates **sync** Mongo + Redis + WhatsApp at **import time**; **Mongo unused**; **Redis** used by **metrics** only.
- **`app.agent.core_agent`** vs **`app.agent.agent`** – Overlapping **CoreAgent** and **agent** exports; **ambiguity** for any **`from app.agent import agent`** (which module wins depends on import order).
- **`app.core.monitoring`** – Broken `get_vector_store` await and **`timing`** indentation; **AlertEngine** / **HealthDashboard** depend on **redis_client** and **MetricsCollector**; **monitoring_loop** not obviously started from main or worker.

---

## 5. Implicit Dependencies

### 5.1 Environment Variables (Uncentralized)

- **Mongo:** `MONGO_URI`, `MONGO_DB_NAME`, `mongodb_uri` (config, unused).
- **Redis:** `REDIS_URL`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_QUEUE_*`.
- **Qdrant:** `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_URL`, `QDRANT_COLLECTION`, `QDRANT_API_KEY`, `EMBEDDING_DIM`.
- **LLM:** `OLLAMA_URL`, `OLLAMA_MODEL`, `OPENAI_API_KEY` (embeddings).
- **Auth:** `JWT_SECRET`.
- **Notion:** `NOTION_TOKEN`, `NOTION_DATABASE_ID`, `NOTION_TASKS_DB_ID`.
- **WhatsApp:** `WHATSAPP_PROVIDER`, `WHATSAPP_VERIFY_TOKEN`.
- **Worker:** `WORKER_MAX_RETRIES`, `WORKER_TIMEOUT_SECONDS`, etc.

### 5.2 Service / Runtime Assumptions

- **MongoDB** and **Qdrant** must be up for **PersistenceManager** and **vector_store**; **Redis** for **worker**, **health**, **status**, **metrics**.
- **Ollama** expected for **LLMClient** when using local model.
- **Streamlit** config (e.g. **core.config**) assumes **Streamlit runtime**; **API/worker** do not.
- **UI** assumes **`/api/v1/stats`** and **`/dashboard/summary`**; **stats** missing; **dashboard** is stub.
- **Docker:** Compose wires **MONGO_URI**, **REDIS_URL**, **QDRANT_***, **OLLAMA_URL**; **worker** command **`python -m app.core.worker`** → **worker will crash** on **MetricsCollector** import before doing any work.

### 5.3 External / Version Dependencies

- **LangChain** (qdrant, openai, community, core); **`langchain_text_splitters`** used but **not in requirements**.
- **`pydantic_settings`** used in **config** but **not in requirements**.
- **OpenAI** embeddings (**vector_store**); **Ollama** for **LLM**; **Notion**, **Twilio/Meta** for **WhatsApp**.
- **`aioredis`** in requirements; **actual code** uses **`redis.asyncio`** → **redundant / legacy** dependency.

---

## 6. Summary Table

| Category | Count | Examples |
|----------|-------|----------|
| **Import / interface bugs** | 10+ | `get_llm`, `MetricsCollector`, `get_agent`, `save_insight`, `ainvoke` vs `ask` |
| **Unmounted / unused modules** | 4+ | **dashboard**, **status** routers; **event_bus**; **redis_layer**; **sharded_store** |
| **Duplicate abstractions** | 6+ | Config, Redis, Mongo, vector stores, **CoreAgent**, **get_current_user** |
| **Missing deps** | 2+ | **langchain_text_splitters**, **pydantic_settings** |
| **Stub / fake endpoints** | 2 | **`/agent/query`**, **`/dashboard/summary`** |
| **Wrong or inconsistent usage** | 5+ | **ingest_batch** `add_texts`, **executor** `get_user_events`, **intelligence_engine** `search_vectors` |

---

## 7. Conclusion

The codebase **encodes a clear vision** (events, RAG, governance, integrations) but is **fragmented** by:

1. **Multiple competing abstractions** for config, Redis, Mongo, vector store, and auth.
2. **Broken or missing symbols** (`get_llm`, `MetricsCollector`, `get_agent`, `save_insight`) and **interface mismatches** (LLM **ainvoke** vs **ask**), leading to **import and runtime failures** in **core paths** (agent, worker, pipeline, webhooks, RAG).
3. **Stub and fake endpoints** in **main** that **override or bypass** real implementations (**dashboard**, **agent query**).
4. **Unmounted routers** (**dashboard**, **status**) and **unused modules** (**event_bus**, **redis_layer**, **sharded_store**), which **add maintenance cost** without benefit.
5. **No single source of truth** for **config**, **events**, or **agent identity**, and **implicit env** assumptions spread across the app.

**Stage 1 output:** This diagnosis only. **No code has been modified.**

---

*Next: **Stage 2 – Vision Reconstruction** (after your confirmation).*
