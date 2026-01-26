# KIRP Enterprise — Capability Mapping

**Date:** 2026-01-26  
**Purpose:** Map current capabilities, missing capabilities, inconsistencies, broken components, and architectural risks

---

## 1. CURRENT CAPABILITIES MAP

### ✅ **FULLY OPERATIONAL**

| Capability | Component | Status | Notes |
|------------|-----------|--------|-------|
| Event Storage | EventStore (MongoDB) | ✅ Complete | Multi-tenant, event-sourced, auditable |
| Vector Storage | RAGEngine (Qdrant) | ✅ Complete | Tenant/space scoping, embeddings |
| Agent Registry | AgentFramework | ✅ Complete | Trigger-based dispatch, tenant scoping |
| Governance | GovernanceEngine (OPA) | ✅ Complete | Policy checks, approvals, audit |
| Event Bus | EventBus | ✅ Complete | Kafka + Redis Streams |
| LLM Client | LLMClient | ✅ Complete | OpenAI, Anthropic, Ollama |
| API Endpoints | FastAPI | ✅ Complete | Ingest, query, agents, governance |
| UI Dashboard | Streamlit | ✅ Complete | Multi-tab interface |
| Infrastructure | Docker Compose | ✅ Complete | Full stack deployment |

### ⚠️ **PARTIALLY OPERATIONAL**

| Capability | Component | Status | Issues |
|------------|-----------|--------|--------|
| Event Pipeline | EventPipeline | ⚠️ 80% | Step 4 skipped, no error recovery, schema not in context |
| RAG Search | RAGEngine | ⚠️ 70% | Zero vector fallback, no BM25, no hybrid, no multi-hop |
| Schema Engine | SchemaEngine | ⚠️ 20% | Stubbed, no models, no persistence |
| Pattern Analysis | PatternAnalyzerAgent | ⚠️ 90% | Works but no validation |
| Planning | TodayTomorrowPlannerAgent | ⚠️ 90% | Works but no validation |
| Forecasting | ForecasterAgent | ⚠️ 90% | Works but no validation |
| Risk Detection | RiskOpportunityAgent | ⚠️ 90% | Works but no validation |
| Meta Orchestration | MetaAgent | ⚠️ 80% | Works but not registered in main.py |

### ❌ **NON-OPERATIONAL / STUBBED**

| Capability | Component | Status | Reason |
|------------|-----------|--------|--------|
| Schema Building | SchemaStructureAgent | ❌ Stub | No LLM extraction, no persistence |
| View Generation | PresentationAgent | ❌ Stub | No Kanban/Timeline/Mindmap logic |
| Self-Improvement | SelfImprovementAgent | ❌ Stub | No log analysis, no improvements |
| Brand Content | OrchestratorAgent (legacy) | ❌ Stub | Returns template text |
| Command Execution | CommandExecutorAgent (legacy) | ❌ Stub | Prints and returns True |
| Insights API | `/api/v1/insights` | ❌ Placeholder | Returns empty list |
| Live Flow | UI tab | ❌ Placeholder | No real-time streaming |
| Scheduled Tasks | Celery tasks | ❌ Missing | daily_intelligence_task, self_improvement_task not defined |

---

## 2. MISSING OR INCOMPLETE CAPABILITIES MAP

### 2.1 Core Engine Gaps

| Capability | Priority | Impact | Effort |
|------------|----------|--------|--------|
| **RAG Zero Vector Fix** | P1 | Critical | Low (1-2 hours) |
| **BM25 + Hybrid Search** | P4 | High | Medium (1-2 days) |
| **Multi-Hop RAG** | P4 | Medium | High (3-5 days) |
| **Schema SQLAlchemy Models** | P2 | Critical | Medium (2-3 days) |
| **Schema Migrations** | P2 | Critical | Low (1 day) |
| **Schema Persistence** | P2 | Critical | Medium (1-2 days) |
| **Error Recovery in Pipeline** | P1 | High | Medium (1-2 days) |
| **Schema in Agent Context** | P2 | High | Low (1 hour) |

### 2.2 Agent Gaps

| Capability | Priority | Impact | Effort |
|------------|----------|--------|--------|
| **SchemaStructureAgent Logic** | P2 | High | Medium (2-3 days) |
| **PresentationAgent Logic** | P3 | Medium | High (3-5 days) |
| **SelfImprovementAgent Logic** | P3 | Medium | High (3-5 days) |
| **JSON Schema Validation** | P4 | Medium | Medium (2-3 days) |
| **MetaAgent Registration** | P2 | Medium | Low (30 min) |
| **Legacy Agent Migration** | P3 | Medium | Medium (2-3 days) |

### 2.3 Integration Gaps

| Capability | Priority | Impact | Effort |
|------------|----------|--------|--------|
| **Kafka Consumers** | P5 | Low | Medium (1-2 days) |
| **RBAC/ABAC APIs** | P5 | Medium | High (5-7 days) |
| **Prometheus Export** | P5 | Low | Medium (1-2 days) |
| **Live Flow Dashboard** | P5 | Low | High (5-7 days) |
| **WebSocket Streaming** | P5 | Low | High (3-5 days) |
| **Scheduled Tasks** | P1 | High | Low (2-3 hours) |

---

## 3. INCONSISTENCIES MAP

### 3.1 Old vs New KIRP

| Aspect | Old KIRP | New KIRP | Integration Status |
|---------|----------|---------|-------------------|
| **Event Storage** | Single MongoDB | MongoDB (events) + Qdrant (vectors) + PostgreSQL (schemas) | ✅ Migrated |
| **RAG** | LangChain QdrantVectorStore | Direct QdrantClient | ✅ Migrated (better) |
| **Agents** | Direct execution | AgentFramework | ⚠️ Partially (legacy stubs) |
| **Governance** | None | OPA-based | ✅ New |
| **Schema** | None | PostgreSQL (stubbed) | ❌ Not integrated |
| **Event Sourcing** | None | Full event sourcing | ✅ New |

### 3.2 Component Inconsistencies

| Issue | Location | Impact | Fix Priority |
|-------|----------|--------|--------------|
| **Agent Registration Duplication** | main.py, tasks.py, kafka_processor.py, whatsapp_os.py | Maintenance burden | P2 |
| **Component Initialization Duplication** | Multiple files | Code duplication | P2 |
| **Legacy Agent Stubs** | compat/legacy_agents.py | Broken APIs | P3 |
| **Schema Engine Not in Context** | pipeline.py | Agents can't use schemas | P2 |
| **MetaAgent Not Registered** | main.py | Cannot use orchestration | P2 |

---

## 4. BROKEN OR UNIMPLEMENTED COMPONENTS

### 4.1 Broken (Immediate Fix Required)

| Component | Issue | Severity | Fix Time |
|-----------|-------|----------|----------|
| **RAGEngine.embed()** | Returns zero vector if embedder fails | 🔴 Critical | 1-2 hours |
| **SchemaEngine.upsert_node()** | TODO, does nothing | 🔴 Critical | 2-3 days |
| **SchemaEngine.list_nodes()** | Returns empty list | 🔴 Critical | 2-3 days |
| **Scheduled Tasks** | Referenced but not defined | 🔴 High | 2-3 hours |
| **GovernanceCheck** | Duplicate risk_score field | 🟡 Medium | 30 min |

### 4.2 Unimplemented (Feature Gaps)

| Component | Missing Feature | Priority | Effort |
|-----------|----------------|----------|--------|
| **RAGEngine** | BM25 search | P4 | 1-2 days |
| **RAGEngine** | Hybrid search | P4 | 1-2 days |
| **RAGEngine** | Multi-hop retrieval | P4 | 3-5 days |
| **SchemaEngine** | SQLAlchemy models | P2 | 2-3 days |
| **SchemaEngine** | Database migrations | P2 | 1 day |
| **SchemaStructureAgent** | LLM extraction | P2 | 2-3 days |
| **PresentationAgent** | View generation | P3 | 3-5 days |
| **SelfImprovementAgent** | Log analysis | P3 | 3-5 days |
| **Agent Framework** | JSON schema validation | P4 | 2-3 days |
| **UI** | Live Flow dashboard | P5 | 5-7 days |
| **API** | RBAC/ABAC endpoints | P5 | 5-7 days |
| **Observability** | Prometheus export | P5 | 1-2 days |

---

## 5. ARCHITECTURAL RISKS

### 5.1 Critical Risks (P1)

| Risk | Component | Impact | Mitigation |
|------|------------|--------|------------|
| **Zero Vector Fallback** | RAGEngine | All searches return identical results | Fix embedder initialization check |
| **No Error Recovery** | EventPipeline | Cascading failures | Add retry logic, partial failure handling |
| **Missing Scheduled Tasks** | Celery | Worker startup failures | Implement missing tasks |

### 5.2 High Risks (P2)

| Risk | Component | Impact | Mitigation |
|------|------------|--------|------------|
| **Schema Engine Stub** | SchemaEngine | No structured data | Implement models + persistence |
| **Schema Not in Context** | EventPipeline | Agents can't query schemas | Pass schema_engine to context |
| **No Validation** | Agents | Unreliable outputs | Add JSON schema validation |

### 5.3 Medium Risks (P3-P4)

| Risk | Component | Impact | Mitigation |
|------|------------|--------|------------|
| **Legacy Agent Stubs** | Brand/Command APIs | Broken endpoints | Migrate to AgentFramework |
| **No Hybrid Search** | RAGEngine | Poor search quality | Add BM25 + hybrid |
| **No Multi-Hop RAG** | RAGEngine | Limited context | Implement iterative retrieval |

### 5.4 Low Risks (P5)

| Risk | Component | Impact | Mitigation |
|------|------------|--------|------------|
| **No Live Flow** | UI | No real-time visibility | Add WebSocket streaming |
| **No RBAC APIs** | Auth | Limited access control | Implement user/role management |
| **No Prometheus** | Observability | Limited metrics | Add metrics export |

---

## 6. CAPABILITY MATURITY MATRIX

| Capability | Current | Target | Gap | Priority |
|------------|--------|--------|-----|----------|
| **Event Storage** | ✅ 100% | ✅ 100% | 0% | - |
| **Vector Storage** | ⚠️ 70% | ✅ 100% | 30% | P4 |
| **Schema Storage** | ❌ 20% | ✅ 100% | 80% | P2 |
| **Agent Framework** | ✅ 100% | ✅ 100% | 0% | - |
| **Agent Implementations** | ⚠️ 60% | ✅ 100% | 40% | P2-P3 |
| **Governance** | ✅ 100% | ✅ 100% | 0% | - |
| **Event Pipeline** | ⚠️ 80% | ✅ 100% | 20% | P1-P2 |
| **API Layer** | ⚠️ 85% | ✅ 100% | 15% | P3 |
| **UI Dashboard** | ⚠️ 90% | ✅ 100% | 10% | P5 |
| **Workers** | ⚠️ 70% | ✅ 100% | 30% | P1 |
| **Observability** | ⚠️ 60% | ✅ 100% | 40% | P5 |
| **Production Hardening** | ⚠️ 50% | ✅ 100% | 50% | P5 |

**Overall System Maturity:** ~65%

---

## 7. INTEGRATION STATUS

### 7.1 Fully Integrated ✅

- EventStore ↔ EventPipeline
- RAGEngine ↔ EventPipeline
- GovernanceEngine ↔ EventPipeline
- AgentFramework ↔ EventPipeline
- EventBus ↔ EventPipeline
- LLMClient ↔ Agents

### 7.2 Partially Integrated ⚠️

- SchemaEngine ↔ EventPipeline (exists but not used)
- SchemaEngine ↔ Agents (not in context)
- Agents ↔ Governance (approval events not processed)
- EventPipeline ↔ UI (no real-time updates)

### 7.3 Not Integrated ❌

- Legacy Agents ↔ AgentFramework
- SchemaEngine ↔ RAGEngine
- Observability ↔ Metrics Collection
- Live Flow ↔ Event Stream

---

## 8. SUMMARY

**Current State:**
- ✅ Core infrastructure: 90% complete
- ⚠️ Agent implementations: 60% complete
- ❌ Schema engine: 20% complete
- ⚠️ RAG enhancements: 70% complete
- ⚠️ Production features: 50% complete

**Critical Gaps:**
1. RAG zero vector (P1)
2. Schema engine (P2)
3. Missing scheduled tasks (P1)
4. Agent stubs (P2-P3)

**Estimated Effort to Production:**
- P1 fixes: 1-2 days
- P2 features: 5-7 days
- P3 features: 5-7 days
- P4 features: 7-10 days
- P5 features: 10-15 days

**Total: ~30-40 days of focused development**
