# KIRP Enterprise — Unified Architecture Plan

**Date:** 2026-01-26  
**Purpose:** Design a clean, modern, unified architecture merging old KIRP intelligence with new Enterprise structure

---

## 1. ARCHITECTURAL PRINCIPLES

### 1.1 Core Principles

1. **Event-Sourced Everything**
   - No state mutation without event
   - Full audit trail
   - Replayable workflows

2. **Multi-Tenant Isolation**
   - Tenant/space/user scoping at every layer
   - Zero cross-tenant leakage
   - RBAC/ABAC enforcement

3. **Controlled Intelligence**
   - Human-in-the-loop governance
   - Explainable decisions
   - Reversible actions

4. **Provider Agnostic**
   - Pluggable LLM providers
   - Pluggable event bus (Kafka/Redis)
   - Pluggable storage backends

5. **Production Ready**
   - Error recovery
   - Observability
   - Scalability

---

## 2. UNIFIED ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────────┐
│                         API LAYER                               │
│  FastAPI: /ingest, /query, /agents, /governance, /whatsapp     │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EVENT PIPELINE (9 Steps)                     │
│  1. Ingest → 2. Store → 3. Embed → 4. Schema → 5. Publish      │
│  6. Agents → 7. Governance → 8. Execute → 9. Emit              │
└─────┬───────────────┬───────────────┬───────────────┬──────────┘
      │               │               │               │
      ▼               ▼               ▼               ▼
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Event    │    │ RAG      │    │ Schema   │    │ Event    │
│ Store    │    │ Engine   │    │ Engine   │    │ Bus      │
│ (Mongo)  │    │ (Qdrant) │    │ (PG)     │    │ (Kafka)  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
      │               │               │               │
      └───────────────┴───────────────┴───────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT FRAMEWORK                              │
│  MetaAgent → PatternAnalyzer, Planner, Forecaster, etc.        │
│  + SchemaStructure, Presentation, SelfImprovement                │
└─────┬───────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GOVERNANCE ENGINE                            │
│  OPA Policies → Risk Scoring → Approvals → Audit                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. LAYER BREAKDOWN

### 3.1 API Layer

**Components:**
- `src/main.py` — FastAPI app, lifecycle management
- `src/api/ingest.py` — Event ingestion
- `src/api/query.py` — RAG queries
- `src/api/agents.py` — Agent management
- `src/api/governance.py` — Approvals, audit
- `src/api/whatsapp_os.py` — WhatsApp integration
- `src/api/brand.py` — Brand content (migrate to PresentationAgent)
- `src/api/command.py` — Commands (migrate to MetaAgent)

**Responsibilities:**
- Request validation
- Authentication/authorization
- Response formatting
- Error handling

---

### 3.2 Core Layer

#### 3.2.1 EventStore
- **Storage:** MongoDB
- **Model:** Event (id, tenant_id, space_id, user_id, content, metadata, embedding, timestamp, sensitivity, event_type, trace_id)
- **Operations:** ingest, get_by_id, list (with scoping)
- **Status:** ✅ Complete

#### 3.2.2 RAGEngine
- **Storage:** Qdrant
- **Features:**
  - Semantic search (Qdrant vectors) ✅
  - BM25/keyword search ❌ → **Add**
  - Hybrid search (semantic + keyword) ❌ → **Add**
  - Multi-hop retrieval ❌ → **Add**
- **Embeddings:** OpenAI (with fallback to local)
- **Status:** ⚠️ 70% (needs hybrid + multi-hop)

#### 3.2.3 SchemaEngine
- **Storage:** PostgreSQL
- **Models:**
  - Task (id, tenant_id, space_id, title, status, metadata, created_at, updated_at)
  - Project (id, tenant_id, space_id, title, tasks[], metadata, created_at, updated_at)
  - LifeArea (id, tenant_id, space_id, title, projects[], metadata, created_at, updated_at)
  - Category (id, tenant_id, space_id, title, items[], metadata, created_at, updated_at)
- **Operations:** upsert_node, list_nodes, get_node, delete_node
- **Status:** ❌ 20% (needs models + persistence)

#### 3.2.4 EventPipeline
- **Steps:**
  1. Ingest event ✅
  2. Store in MongoDB ✅
  3. Generate embedding → Qdrant ✅
  4. Store metadata → PostgreSQL ⚠️ (skipped, needs fix)
  5. Publish to event bus ✅
  6. Trigger agents ✅
  7. Governance check ✅
  8. Execute action ✅
  9. Emit completion event ✅
- **Context passed to agents:**
  - `rag_response` ✅
  - `events` ✅
  - `trace_id` ✅
  - `schema_engine` ❌ → **Add**
  - `schema_nodes` ❌ → **Add**
- **Status:** ⚠️ 80% (needs schema in context, error recovery)

#### 3.2.5 GovernanceEngine
- **Provider:** OPA (Open Policy Agent)
- **Features:**
  - Policy checks ✅
  - Risk scoring ✅
  - Approval workflows ✅
  - Audit logging ✅
- **Status:** ✅ Complete (minor: duplicate risk_score field)

#### 3.2.6 AgentFramework
- **Registry:** AgentSpec (name, type, triggers, tools, autonomy, tenant_scopes, handler)
- **Operations:** register, get, list_by_trigger, list_all, run
- **Status:** ✅ Complete

#### 3.2.7 EventBus
- **Providers:** Kafka (`confluent-kafka` in `src/core/integrations.py`). **Redis Streams as a bus is not implemented in `src/`** — see `docs/RUNTIME_REALITY_MATRIX.md`.
- **Operations:** connect, publish, close
- **Status:** ✅ Complete

#### 3.2.8 LLMClient
- **Providers:** OpenAI, Anthropic, Ollama
- **Operations:** invoke, ainvoke
- **Status:** ✅ Complete

---

### 3.3 Agent Layer

#### 3.3.1 MetaAgent ✅
- **Purpose:** Orchestrate all agents
- **Features:** LLM-based routing, multi-agent coordination
- **Status:** ✅ Complete (needs registration in main.py)

#### 3.3.2 Analysis Agents ✅
- **PatternAnalyzerAgent:** Habits, overload, procrastination
- **RiskOpportunityAgent:** Risks, opportunities, follow-ups
- **ForecasterAgent:** Load, bottlenecks, issues
- **Status:** ✅ Complete (needs JSON validation)

#### 3.3.3 Planning Agents ✅
- **TodayTomorrowPlannerAgent:** Daily/weekly plans
- **Status:** ✅ Complete (needs JSON validation)

#### 3.3.4 Schema Agents ❌
- **SchemaStructureAgent:** Extract tasks/projects from events
  - **Needs:** LLM extraction, schema node creation, persistence
- **Status:** ❌ Stub

#### 3.3.5 Presentation Agents ❌
- **PresentationAgent:** Generate Kanban/Timeline/Mindmap views
  - **Needs:** View generation logic, schema integration
- **Status:** ❌ Stub

#### 3.3.6 Improvement Agents ❌
- **SelfImprovementAgent:** Learn from logs, improve prompts
  - **Needs:** Log analysis, improvement suggestions, event emission
- **Status:** ❌ Stub

---

### 3.4 Integration Layer

#### 3.4.1 WhatsApp Integration ✅
- **Features:** Daily intelligence, command execution, conversational queries
- **Status:** ✅ Complete

#### 3.4.2 Legacy Agents ⚠️
- **OrchestratorAgent:** Brand content (stub)
- **CommandExecutorAgent:** Command execution (stub)
- **Migration Plan:** Replace with PresentationAgent + MetaAgent
- **Status:** ⚠️ Stubs

---

### 3.5 Worker Layer

#### 3.5.1 Celery Workers ✅
- **Tasks:** ingest_task, whatsapp_send_task
- **Scheduled:** daily_intelligence_task, self_improvement_task
- **Status:** ⚠️ Missing scheduled task implementations

#### 3.5.2 Kafka Processor ✅
- **Purpose:** Consume events from Kafka, run pipeline
- **Status:** ✅ Complete

---

### 3.6 UI Layer

#### 3.6.1 Master Dashboard ✅
- **Tabs:** Intelligence, Risks, Search, Agents, Health, Governance, Insights, Live Flow
- **Status:** ✅ Complete (Live Flow is placeholder)

---

## 4. DATA FLOW

### 4.1 Ingest Flow

```
User → API /ingest
  → EventPipeline.run()
    → 1. Create Event
    → 2. Store in MongoDB
    → 3. Generate embedding → Qdrant
    → 4. Extract schema nodes → PostgreSQL (NEW)
    → 5. Publish to event bus
    → 6. Trigger agents (with schema in context)
    → 7. Governance check
    → 8. Execute action
    → 9. Emit completion event
```

### 4.2 Query Flow

```
User → API /query
  → RAGEngine.search()
    → Hybrid search (semantic + BM25) (NEW)
    → Multi-hop retrieval (NEW)
    → Return context + results
```

### 4.3 Agent Flow

```
Event → AgentFramework.list_by_trigger()
  → MetaAgent.route() (optional)
    → Agent.run(context)
      → Context includes: rag_response, events, schema_engine, schema_nodes (NEW)
      → LLM processing
      → JSON schema validation (NEW)
      → Return result
        → If requires_approval → Governance
        → If schema_update → SchemaEngine.upsert_node()
```

---

## 5. INTEGRATION POINTS

### 5.1 EventPipeline ↔ SchemaEngine

**Current:** Schema engine not used in pipeline  
**Target:** Step 4 extracts and stores schema nodes

**Implementation:**
```python
# In EventPipeline.run(), after embedding:
schema_nodes = await self._extract_schema_nodes(ev, emb)
for node in schema_nodes:
    await self._schema.upsert_node(node)

# Pass to agents:
ctx["schema_engine"] = self._schema
ctx["schema_nodes"] = schema_nodes
```

### 5.2 Agents ↔ SchemaEngine

**Current:** Agents don't have schema access  
**Target:** Agents can query/update schemas

**Implementation:**
- Pass `schema_engine` in context
- SchemaStructureAgent extracts and persists
- PresentationAgent queries schemas for views

### 5.3 RAGEngine ↔ SchemaEngine

**Current:** No bidirectional link  
**Target:** Schema nodes enhance RAG queries

**Implementation:**
- RAG queries can filter by schema node IDs
- Schema nodes can include RAG result references

### 5.4 Governance ↔ Agents

**Current:** Approval events not processed  
**Target:** Agents check approval status before execution

**Implementation:**
- Agent results include `requires_approval` flag
- Pipeline checks approval events before step 8

---

## 6. MIGRATION FROM OLD KIRP

### 6.1 Legacy Agents

**OrchestratorAgent → PresentationAgent**
- Brand content generation → View generation
- Use schema nodes for context

**CommandExecutorAgent → MetaAgent**
- Command execution → Agent routing
- Use MetaAgent to route to appropriate agent

### 6.2 Data Migration

**Old MongoDB → New Architecture**
- Events → EventStore (MongoDB)
- Vectors → RAGEngine (Qdrant)
- Schemas → SchemaEngine (PostgreSQL)

**Migration Script:** (to be created)
- Read from old MongoDB
- Transform to new Event model
- Ingest via EventPipeline

---

## 7. PRODUCTION HARDENING

### 7.1 Error Recovery

**EventPipeline:**
- Retry logic for transient failures
- Partial failure handling (store event even if embedding fails)
- Dead letter queue for failed events

**RAGEngine:**
- Fallback to keyword search if embedding fails
- Retry logic for Qdrant operations

### 7.2 Observability

**Metrics:**
- Event ingestion rate
- RAG query latency
- Agent execution time
- Governance check latency
- Error rates

**Tracing:**
- Trace ID propagation through pipeline
- Agent execution traces
- Governance decision traces

**Logging:**
- Structured logging (JSON)
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Context (tenant_id, user_id, trace_id)

### 7.3 Scalability

**Horizontal Scaling:**
- Stateless API servers
- Worker pool (Celery)
- Kafka consumers (multiple instances)

**Vertical Scaling:**
- Connection pooling (MongoDB, PostgreSQL)
- Async operations throughout
- Caching (Redis) for frequent queries

---

## 8. SECURITY

### 8.1 Multi-Tenant Isolation

- Tenant ID in every query
- Space ID for sub-isolation
- User ID for personal data
- Sensitivity levels (PRIVATE, SHARED, CONFIDENTIAL)

### 8.2 Access Control

- RBAC: Role-based access control (admin, member, viewer)
- ABAC: Attribute-based access control (OPA policies)
- API authentication (JWT)
- API authorization (per-endpoint checks)

### 8.3 Data Protection

- Encryption at rest (database level)
- Encryption in transit (TLS)
- Audit logging (all actions logged)
- Data retention policies

---

## 9. TESTING STRATEGY

### 9.1 Unit Tests

- Core components (EventStore, RAGEngine, SchemaEngine)
- Agents (each agent independently)
- Governance (policy checks)

### 9.2 Integration Tests

- EventPipeline (full 9-step flow)
- Agent framework (trigger → execution)
- RAG + Schema integration

### 9.3 E2E Tests

- Full ingest → query flow
- Agent execution → governance → approval
- Multi-tenant isolation

---

## 10. DEPLOYMENT

### 10.1 Docker Compose (Current)

- All services containerized ✅
- Health checks ✅
- Network isolation ✅

### 10.2 Kubernetes (Future)

- Horizontal pod autoscaling
- Service mesh (Istio)
- ConfigMaps/Secrets
- Persistent volumes

---

## 11. SUMMARY

**Architecture Strengths:**
- ✅ Event-sourced foundation
- ✅ Multi-tenant isolation
- ✅ Governance integration
- ✅ Agent framework
- ✅ Provider agnostic

**Architecture Gaps:**
- ❌ Schema engine incomplete
- ❌ RAG enhancements missing
- ❌ Agent stubs
- ❌ Error recovery
- ❌ Production observability

**Unified Design:**
- Merges old KIRP intelligence (agents, RAG) with new Enterprise structure (event sourcing, governance, multi-tenancy)
- Clean separation of concerns
- Extensible and maintainable

**Next Steps:**
1. Implement missing components (P1-P2)
2. Add enhancements (P3-P4)
3. Production hardening (P5)
