# KIRP Enterprise — Implementation Plan (Prioritized)

**Date:** 2026-01-26  
**Purpose:** Step-by-step execution plan for completing KIRP Enterprise

---

## PRIORITY BREAKDOWN

### P1 — Core Stabilization (1-2 days)
**Goal:** Fix critical bugs, ensure system runs end-to-end

### P2 — Schema Engine (5-7 days)
**Goal:** Complete schema persistence, enable structured data

### P3 — Legacy Cleanup (2-3 days)
**Goal:** Remove/integrate legacy agents, unify architecture

### P4 — Intelligence Upgrade (7-10 days)
**Goal:** Add BM25, multi-hop RAG, MetaAgent, JSON validation

### P5 — Production Hardening (10-15 days)
**Goal:** Kafka consumers, RBAC/ABAC, observability, Live Flow

---

## P1 — CORE STABILIZATION

### Task 1.1: Fix RAG Zero Vector Fallback ⏱️ 1 hour
**File:** `src/core/rag_engine.py`

**Issue:** Returns `[0.0] * 1536` if embedder not initialized

**Fix:**
```python
async def embed(self, text: str) -> list[float]:
    if self._embedder is None:
        await self.connect()  # Try to initialize
        if self._embedder is None:
            raise ValueError("Embedder not initialized. Check OPENAI_API_KEY or embedding provider.")
    emb = await self._embedder.aembed_query(text)
    if not emb or len(emb) == 0:
        raise ValueError("Embedding generation failed")
    return emb
```

**Test:** Verify embedding generation works, fails gracefully if API key missing

---

### Task 1.2: Implement Missing Scheduled Tasks ⏱️ 2-3 hours
**File:** `src/workers/tasks.py`

**Issue:** `daily_intelligence_task` and `self_improvement_task` referenced but not defined

**Fix:**
```python
@celery_app.task(bind=True, name="daily_intelligence_task")
def daily_intelligence_task(self: Any, user_id: str, tenant_id: str, space_id: str) -> dict[str, Any]:
    """Generate and send daily intelligence via WhatsApp."""
    import asyncio
    async def _run():
        from src.api.whatsapp_os import daily_intelligence
        return await daily_intelligence(user_id=user_id, tenant_id=tenant_id, space_id=space_id)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    out = loop.run_until_complete(_run())
    loop.close()
    return out

@celery_app.task(bind=True, name="self_improvement_task")
def self_improvement_task(self: Any, tenant_id: str) -> dict[str, Any]:
    """Run self-improvement analysis."""
    import asyncio
    async def _run():
        from src.core.event_store import EventStore
        from src.core.rag_engine import RAGEngine
        from src.core.agent_framework import AgentFramework
        from src.agents.self_improvement import self_improvement_spec
        import os
        
        store = EventStore(os.getenv("MONGO_URI"))
        await store.connect()
        rag = RAGEngine(qdrant_url=os.getenv("QDRANT_URL"))
        await rag.connect()
        af = AgentFramework()
        af.register(self_improvement_spec)
        
        # Get recent events for analysis
        events = await store.list(tenant_id=tenant_id, limit=100)
        rag_resp = await rag.search("recent activity", tenant_id=tenant_id, limit=10)
        
        ctx = {"rag_response": rag_resp, "events": events, "logs": []}
        result = await af.run("SelfImprovementAgent", tenant_id, "private", "system", ctx)
        return result
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    out = loop.run_until_complete(_run())
    loop.close()
    return out
```

**Test:** Verify Celery can start without errors, tasks execute

---

### Task 1.3: Fix GovernanceCheck Duplicate Field ⏱️ 30 min
**File:** `src/core/governance.py`

**Issue:** Duplicate `risk_score` field (line 37-38)

**Fix:** Remove duplicate line 38

---

### Task 1.4: Add Error Recovery to EventPipeline ⏱️ 1-2 days
**File:** `src/core/pipeline.py`

**Issue:** No retry logic, cascading failures

**Fix:**
- Add retry decorator for transient failures
- Partial failure handling (store event even if embedding fails)
- Dead letter queue for failed events
- Logging for all failures

---

### Task 1.5: Pass Schema Engine to Agents ⏱️ 1 hour
**File:** `src/core/pipeline.py`

**Issue:** Schema engine not in agent context

**Fix:**
```python
# In EventPipeline.run(), step 6:
ctx = {
    "rag_response": rag_resp,
    "events": [ev],
    "trace_id": trace_id,
    "schema_engine": self._schema,  # ADD
    "schema_nodes": [],  # ADD (populate from step 4)
}
```

---

## P2 — SCHEMA ENGINE

### Task 2.1: Create SQLAlchemy Models ⏱️ 1 day
**File:** `src/models/schema.py`

**Models:**
- `Task` (id, tenant_id, space_id, title, status, priority, metadata, created_at, updated_at)
- `Project` (id, tenant_id, space_id, title, tasks[], metadata, created_at, updated_at)
- `LifeArea` (id, tenant_id, space_id, title, projects[], metadata, created_at, updated_at)
- `Category` (id, tenant_id, space_id, title, items[], metadata, created_at, updated_at)

**Relationships:**
- Project → Tasks (one-to-many)
- LifeArea → Projects (one-to-many)
- Category → Items (polymorphic)

---

### Task 2.2: Create Database Migrations ⏱️ 1 day
**File:** `alembic/versions/002_schema_models.py`

**Migration:**
- Create tables for Task, Project, LifeArea, Category
- Add indexes (tenant_id, space_id, created_at)
- Add foreign keys

---

### Task 2.3: Implement SchemaEngine Persistence ⏱️ 2-3 days
**File:** `src/core/schema_engine.py`

**Implement:**
- `upsert_node()` — Insert or update schema node
- `list_nodes()` — Query with filters
- `get_node()` — Get single node by ID
- `delete_node()` — Soft delete

**Use:** SQLAlchemy async session factory

---

### Task 2.4: Implement SchemaStructureAgent ⏱️ 2-3 days
**File:** `src/agents/schema_structure.py`

**Logic:**
1. Extract tasks/projects from RAG context using LLM
2. Create SchemaNode objects
3. Upsert via SchemaEngine
4. Return created/updated nodes

**LLM Prompt:**
```
Extract structured entities from this context:
- Tasks (with status, priority)
- Projects (with tasks)
- Life Areas (with projects)
- Categories

Return JSON with entities.
```

---

## P3 — LEGACY CLEANUP

### Task 3.1: Migrate Brand API to PresentationAgent ⏱️ 1 day
**File:** `src/api/brand.py`

**Change:**
- Remove OrchestratorAgent dependency
- Use PresentationAgent with view_type="brand_content"
- Pass idea as context

---

### Task 3.2: Migrate Command API to MetaAgent ⏱️ 1 day
**File:** `src/api/command.py`

**Change:**
- Remove CommandExecutorAgent dependency
- Use MetaAgent.route() to route command
- Execute routed agent

---

### Task 3.3: Centralize Agent Registration ⏱️ 1 day
**File:** `src/core/agent_framework.py` or new `src/core/agent_registry.py`

**Create:**
- `register_all_agents()` function
- Import all agent specs
- Register in one place

**Update:**
- `main.py`, `tasks.py`, `kafka_processor.py`, `whatsapp_os.py` to use centralized function

---

## P4 — INTELLIGENCE UPGRADE

### Task 4.1: Add BM25 Search to RAGEngine ⏱️ 1-2 days
**File:** `src/core/rag_engine.py`

**Implementation:**
- Use `rank_bm25` library or Elasticsearch
- Index text content for keyword search
- Combine with semantic search scores

**Hybrid Score:**
```python
final_score = 0.7 * semantic_score + 0.3 * bm25_score
```

---

### Task 4.2: Add Multi-Hop RAG ⏱️ 3-5 days
**File:** `src/core/rag_engine.py`

**Implementation:**
1. Initial retrieval (semantic + BM25)
2. Extract entities/keywords from results
3. Second retrieval using extracted terms
4. Merge and re-rank results
5. Return enriched context

**Iterations:** 2-3 hops max

---

### Task 4.3: Register MetaAgent in main.py ⏱️ 30 min
**File:** `src/main.py`

**Fix:**
```python
from src.agents.meta_agent import meta_agent_spec
# Add to registration list
```

---

### Task 4.4: Add JSON Schema Validation ⏱️ 2-3 days
**File:** `src/core/agent_framework.py`

**Implementation:**
- Define JSON schemas for each agent output
- Validate agent results before returning
- Log validation errors
- Return structured errors

**Schemas:**
- PatternAnalyzer: `{"patterns": [...], "summary": "..."}`
- Planner: `{"today": [...], "tomorrow": [...], "critical": [...]}`
- Forecaster: `{"tomorrow_load": "...", "bottlenecks": [...], "upcoming_issues": [...]}`
- RiskOpportunity: `{"risks": [...], "opportunities": [...], "missed_follow_ups": [...]}`

---

## P5 — PRODUCTION HARDENING

### Task 5.1: Implement Kafka Consumers ⏱️ 1-2 days
**File:** `src/workers/kafka_consumer.py` (new)

**Implementation:**
- Consumer group for event processing
- Offset management
- Error handling and retries
- Dead letter queue

---

### Task 5.2: Add RBAC/ABAC APIs ⏱️ 5-7 days
**Files:** `src/api/rbac.py`, `src/api/abac.py` (new)

**Endpoints:**
- `/rbac/users` — User management
- `/rbac/roles` — Role management
- `/rbac/permissions` — Permission management
- `/abac/policies` — Policy management

**Integration:**
- Connect to GovernanceEngine
- User/role storage in PostgreSQL

---

### Task 5.3: Add Prometheus Metrics Export ⏱️ 1-2 days
**File:** `src/api/observability.py`

**Metrics:**
- Event ingestion rate
- RAG query latency
- Agent execution time
- Governance check latency
- Error rates

**Endpoint:** `/observability/metrics` (Prometheus format)

---

### Task 5.4: Implement Live Flow Dashboard ⏱️ 5-7 days
**Files:** `src/ui/realtime.py`, `src/api/realtime.py` (new)

**Implementation:**
- WebSocket server for real-time events
- Stream events from Kafka/Redis
- Update UI in real-time
- Filter by tenant/space/user

---

## EXECUTION ORDER

### Week 1: P1 (Core Stabilization)
- Day 1: Tasks 1.1, 1.2, 1.3, 1.5
- Day 2: Task 1.4 (error recovery)

### Week 2: P2 (Schema Engine)
- Day 1-2: Task 2.1 (models)
- Day 3: Task 2.2 (migrations)
- Day 4-5: Task 2.3 (persistence)
- Day 6-7: Task 2.4 (SchemaStructureAgent)

### Week 3: P3 (Legacy Cleanup) + P4 Start
- Day 1: Task 3.1 (Brand API)
- Day 2: Task 3.2 (Command API)
- Day 3: Task 3.3 (Agent registration)
- Day 4-5: Task 4.1 (BM25)
- Day 6-7: Task 4.3 (MetaAgent registration)

### Week 4: P4 (Intelligence Upgrade)
- Day 1-3: Task 4.2 (Multi-hop RAG)
- Day 4-5: Task 4.4 (JSON validation)

### Week 5-6: P5 (Production Hardening)
- Week 5: Tasks 5.1, 5.2 (Kafka, RBAC)
- Week 6: Tasks 5.3, 5.4 (Prometheus, Live Flow)

---

## SUCCESS CRITERIA

### P1 Complete When:
- ✅ RAGEngine never returns zero vectors
- ✅ All scheduled tasks defined and working
- ✅ EventPipeline has error recovery
- ✅ Agents receive schema in context

### P2 Complete When:
- ✅ SQLAlchemy models created and migrated
- ✅ SchemaEngine persists data
- ✅ SchemaStructureAgent extracts and stores schemas

### P3 Complete When:
- ✅ Legacy agents removed or migrated
- ✅ Agent registration centralized
- ✅ All APIs use AgentFramework

### P4 Complete When:
- ✅ BM25 + hybrid search working
- ✅ Multi-hop RAG implemented
- ✅ MetaAgent registered and working
- ✅ JSON schema validation on all agents

### P5 Complete When:
- ✅ Kafka consumers operational
- ✅ RBAC/ABAC APIs functional
- ✅ Prometheus metrics exported
- ✅ Live Flow dashboard streaming events

---

## RISK MITIGATION

### High Risk Items:
1. **Schema Engine Complexity** — Mitigate by starting simple, iterating
2. **Multi-Hop RAG Performance** — Mitigate by limiting hops, caching
3. **RBAC/ABAC Complexity** — Mitigate by using existing OPA policies

### Testing Strategy:
- Unit tests for each component
- Integration tests for pipelines
- E2E tests for full flows
- Load tests for production readiness

---

## ESTIMATED TOTAL EFFORT

- **P1:** 1-2 days
- **P2:** 5-7 days
- **P3:** 2-3 days
- **P4:** 7-10 days
- **P5:** 10-15 days

**Total: 25-37 days** (~5-7 weeks)
