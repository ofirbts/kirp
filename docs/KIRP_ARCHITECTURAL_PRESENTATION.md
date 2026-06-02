# KIRP Intelligence OS — Architectural Presentation Blueprint

**7-Minute Talk for Senior Interview / Admission Committee**

Production-grade, technically honest content. All claims rooted in actual codebase; gaps and assumptions explicitly labeled.

---

## High-Level Summary

- **KIRP** is an event-sourced Intelligence OS: a controlled layer that ingests content, stores events, embeds in vectors, extracts life objects (tasks, commitments), and surfaces them via RAG and agents—all with strict multi-tenant isolation.
- **Core insight:** “Everything is an Event.” No state mutation without an event. Events flow: API → Kafka → pipeline → Mongo (source of truth), Qdrant (vectors), Postgres (schema). This enables auditability, replayability, and a clear source of truth.
- **Unified stack:** FastAPI API, Kafka event bus, agent processor worker, polyglot persistence (MongoDB events, Postgres schema, Qdrant vectors), OPA governance, Prometheus metrics.
- **Engineering honesty:** Current state is PoC-to-production-grade. Schema engine and RAG are partially implemented; some agents are stubs. Production hardening (error recovery, full observability, security review) is planned, not complete.
- **Demonstrates:** System thinking, event-sourcing, multi-tenancy, controlled AI (governance + agents), and honest assessment of what is built vs. intended.

---

## Slides

### Slide 1: Identity & Vision

**Title:** KIRP Intelligence OS — Executive Function Layer for Distributed Systems

**Bullets:**
- KIRP is an **Intelligence OS**: a controlled layer between humans, tools, and AI that ingests, remembers, reasons, and surfaces knowledge—without direct DB mutations.
- Think of it as an **Executive Function Layer**: it provides context, prioritization, and action routing for life data (tasks, commitments, events) across sources.
- North Star: **Controlled Intelligence · Event-Sourced · Multi-Tenant · Zero Leakage.**

**Speaker script:**  
“I built KIRP as an Intelligence OS—not a chatbot. It’s an executive function layer: it ingests content from email, Notion, WhatsApp; stores it as immutable events; embeds it for semantic search; extracts tasks and commitments; and surfaces them via a dashboard, RAG, and agents. Everything is event-sourced. Every change is an event, which gives us auditability and replayability.”

**Visual suggestion:**  
Diagram: Human → KIRP (Ingest / Store / RAG / Agents) → Dashboard + Integrations. “Executive function” in the center.

---

### Slide 2: The Problem

**Title:** Context Collapse & Cognitive Overload

**Bullets:**
- **Context collapse:** Knowledge lives in many silos (email, Notion, Slack, calendar). No single place that “knows you” and can answer “What should I focus on today?”
- **Cognitive overload:** Too many inputs, too few prioritization mechanisms. Humans need a system that filters, summarizes, and suggests—not raw streams.
- ** lack of executive function:** Distributed systems and humans both need an orchestration layer that routes, delegates, and enforces policy.

**Speaker script:**  
“The problem is context collapse and cognitive overload. Your tasks live in Notion, your emails in Gmail, your messages in Slack. There’s no unified layer that remembers, reasons, and suggests. KIRP is that layer: it ingests from multiple sources, stores events, and gives you a single place to ask, ‘What should I focus on today?’ with answers grounded in your own data.”

**Visual suggestion:**  
Fragmented bubbles (Email, Notion, Slack, Calendar) flowing into one central brain shape.

---

### Slide 3: Architectural Insight — Everything is an Event

**Title:** Everything is an Event — Auditability, Replayability, Source of Truth

**Bullets:**
- **No state mutation without an event.** Every write—ingest, agent run, schema update—goes through an event. Events are append-only and immutable.
- **Event flow:** API receives request → governance check → event created → stored in MongoDB (source of truth) → embedded in Qdrant → schema nodes in Postgres → optionally published to Kafka for async processing.
- **What this enables:** Full audit trail; replay for debugging; idempotency (Redis) for Kafka consumers; clear source of truth (Mongo for events).

**Speaker script:**  
“The main architectural insight is: everything is an event. When you ingest content, we create an event. We store it in MongoDB as the source of truth, embed it in Qdrant for semantic search, and extract life objects into Postgres. We can replay, audit, and reason about the system. The Kafka processor consumes events with idempotency keys in Redis—no duplicate processing.”

**Visual suggestion:**  
Flow: Ingest → Event → Mongo → Qdrant + Postgres. “Append-only, immutable” label on the event store.

---

### Slide 4: Unified Backend — FastAPI + Kafka + Workers + Polyglot Persistence

**Title:** Unified Backend Architecture

**Bullets:**
- **API layer:** FastAPI. Ingest, Ask, Query, Tasks, History, Agents, Graph, Governance. JWT auth; tenant context from request.state.user.
- **Event bus:** Kafka (`kirp-events` topic). Producer on ingest; consumer (kirp-agent-processor) runs full pipeline (EventRegistry → handlers).
- **Polyglot persistence:** MongoDB (EventStore + History), Postgres (SchemaEngine: tasks, commitments, projects, life areas), Qdrant (vectors for RAG). Redis for idempotency.

**Speaker script:**  
“The backend is unified: FastAPI for all APIs, Kafka as the event bus, and a processor worker that consumes events. We use polyglot persistence on purpose: MongoDB for events and history, Postgres for relational schema and tasks, Qdrant for vector search. Each store has a clear role.”

**Visual suggestion:**  
Stack diagram: FastAPI (top) → Kafka (middle) → Mongo / Postgres / Qdrant / Redis (bottom).

---

### Slide 5: Agents & Governance

**Title:** Meta-Agent + Specialized Agents, Policies Over LLMs

**Bullets:**
- **Agent framework:** AgentSpec (name, type, triggers, tools, autonomy, tenant_scopes). Agents registered centrally (PatternAnalyzer, Planner, Forecaster, RiskOpportunity, SchemaStructure, MetaAgent, ReminderAgent, InsightAgentV2, ExecutionAgent, OverloadAgent, ConflictAgent).
- **Governance:** OPA policies (kirp.rego). Tenant isolation, space access, role checks, risk scoring. All writes go through `GovernanceEngine.check()`.
- **Controlled intelligence:** Autonomy levels (FULL, SEMI, HUMAN_IN_LOOP). LLMs used only through registered agents; RAG context passed explicitly.

**Speaker script:**  
“Agents are registered in a framework with triggers, autonomy levels, and tenant scoping. We have planners, insight agents, reminder agents, and a meta-agent for orchestration. Governance is policy-first: OPA enforces tenant isolation, space access, and risk scoring. No LLM call bypasses the governance layer.”

**Visual suggestion:**  
MetaAgent at top, specialized agents below; OPA box on the side with “Policy” label.

---

### Slide 6: Engineering Reality Check — PoC vs Production

**Title:** What’s Built, What’s Not, Why It Matters

**Bullets:**
- **What works:** Ingest → EventStore → RAG → Schema (life-object extraction) → History; Kafka processor with idempotency; multi-tenant JWT + tenant context; dashboard (Tasks, History, Insights, Graph, Second Brain); Ask/Think via InsightAgent + RAG.
- **What’s incomplete:** Schema engine ~20% (per UNIFIED_ARCHITECTURE); RAG hybrid search ~70%; some agents are stubs (SchemaStructure, Presentation, SelfImprovement); error recovery (dead-letter, partial failure) not fully implemented.
- **Responsible decisions:** SKIP_AUTH and dev fallbacks only when explicitly enabled; shutdown/restrict production when secrets or exposure risk exists; production checklist documented but not fully enforced.

**Speaker script:**  
“I’m honest: this is PoC-to-production-grade. The core flow works—ingest, store, embed, extract tasks, surface in the dashboard. But the schema engine and RAG enhancements are partial; some agents are stubs. When we had a key exposure risk, we shut down production. That’s the kind of tradeoff I make: ship when safe, don’t pretend it’s fully hardened.”

**Visual suggestion:**  
Two columns: “Production-ready” (event flow, multi-tenancy, governance) vs. “Needs work” (schema completeness, RAG hybrid, error recovery).

---

### Slide 7: Observability & Trust

**Title:** Observability & Why the System Is Trustworthy

**Bullets:**
- **Metrics:** Prometheus MetricsCollector. Counters, gauges, histograms for events, RAG, agents. DISABLE_PROMETHEUS=1 on worker to avoid multiprocess conflicts.
- **Audit:** History 2.0 (human-readable timeline); OPA governance decisions; event trace_ids propagated through pipeline.
- **Trust:** Immutable events, policy-based governance, tenant isolation at every layer. You can audit what happened and why.

**Speaker script:**  
“We use Prometheus metrics for events, RAG latency, and agent runs. History entries are human-readable. OPA logs governance decisions. Trace IDs flow through the pipeline. The system is trustworthy because you can see what happened, who did it, and whether policy allowed it.”

**Visual suggestion:**  
Metrics → Prometheus; Audit → History + OPA; Trust → Immutability + Policy.

---

### Slide 8: Tech Stack

**Title:** Tech Stack by Layer

**Bullets:**
- **Data:** MongoDB (events, history), PostgreSQL (schema, tasks), Qdrant (vectors), Redis (idempotency).
- **Events:** Kafka (event bus), Confluent Kafka Python client.
- **Brain:** RAGEngine (Qdrant + OpenAI embeddings, BM25 hybrid), InsightAgent, AgentFramework.
- **Governance:** OPA (Open Policy Agent), kirp.rego policies.
- **Connectivity:** FastAPI, JWT, WebSocket (notifications).
- **Observability:** Prometheus, structured logs, trace IDs.

**Speaker script:**  
“The stack is intentional: Mongo for events, Postgres for schema, Qdrant for vectors. Kafka for the event bus. OPA for governance. Prometheus for metrics. Each choice has a clear role.”

**Visual suggestion:**  
Table or layered diagram: Data | Events | Brain | Governance | Connectivity | Observability.

---

### Slide 9: Roadmap & Evolution

**Title:** Where This Architecture Can Go Next

**Bullets:**
- **Near term:** Schema engine completion (nodes/edges in context for agents); RAG hybrid + multi-hop; error recovery (dead-letter queue, partial failure handling).
- **Medium term:** Real-time dashboard updates (WebSocket for tasks/activity); Connectors OAuth with tenant scoping; Life Graph lazy-loading for large graphs.
- **Long term:** Kubernetes deployment; horizontal scaling of workers; full production hardening (security review, backup/restore validation).

**Speaker script:**  
“The architecture is designed to evolve. Next steps: complete the schema engine, add RAG hybrid and multi-hop, and implement error recovery. Then real-time updates, connector OAuth, and eventually Kubernetes and full production hardening.”

**Visual suggestion:**  
Timeline: Near → Medium → Long. Bullets under each.

---

### Slide 10: Why Me — What This Demonstrates

**Title:** What This Demonstrates About Me as an Architect

**Bullets:**
- **System thinking:** Event-sourcing, polyglot persistence, and clear separation of concerns—not a monolith.
- **Production mindset:** Multi-tenancy from day one; idempotency; governance before execution; honest about gaps.
- **Controlled AI:** No LLM calls outside the agent framework; RAG context passed explicitly; policies constrain behavior.
- **Responsible engineering:** Shutdown when risks emerge; documented production checklist; no invented features in this presentation.

**Speaker script:**  
“This project shows how I think: event-sourcing from the ground up, multi-tenancy baked in, governance before execution. I don’t call LLMs directly; I route through agents with policies. And I’m honest about what’s built versus what’s intended. That’s the kind of architect I am.”

**Visual suggestion:**  
Four quadrants: System Thinking | Production Mindset | Controlled AI | Honest Assessment.

---

## Engineering Honesty / Reality Check

### What Is NOT in Production Right Now

- **Full schema engine:** Life-object extraction works; schema nodes are stored. But schema-in-context for agents and bidirectional RAG↔Schema are incomplete (per UNIFIED_ARCHITECTURE).
- **RAG enhancements:** BM25 hybrid exists in code; multi-hop retrieval is stubbed. Production RAG is primarily semantic (Qdrant).
- **Some agents are stubs:** SchemaStructure, Presentation, SelfImprovement have specs but limited or no handler logic.
- **Error recovery:** No dead-letter queue; partial failure handling (e.g., store event even if embedding fails) is best-effort. Retries exist in Kafka processor; backpressure is not fully designed.
- **Full production hardening:** JWT rotation, CORS, backup strategies are documented but not necessarily validated in production. Prometheus multiproc dir handling; DISABLE_PROMETHEUS=1 used on worker to avoid conflicts.

### Risks and Gaps

- **Security:** JWT and tenant context are enforced; OPA policies exist. A full security review (penetration testing, dependency audit) has not been performed.
- **Scaling:** Stateless API; workers can scale horizontally. Kafka consumer group supports multiple instances. Connection pooling and async patterns are in place; load testing for high throughput is not documented.
- **UX polish:** Dashboard features (Tasks, History, Think, Second Brain) work; real-time updates and advanced filtering could be improved.
- **Assumption:** The user mentioned “shutting down production after key exposure”—this is treated as a responsible decision demonstrating risk awareness. *If this did not happen, remove or rephrase.*

### Why the Decisions Demonstrate Responsible Engineering

- **Explicit dev fallbacks:** SKIP_AUTH and default tenant/user only when explicitly enabled; production requires JWT and valid tenant_id/user_id.
- **No silent overrides:** Tenant context from JWT is never silently replaced with “dev” when a real user exists.
- **Idempotency:** Kafka processor uses Redis idempotency keys; duplicate events are skipped.
- **Governance first:** Every write path goes through GovernanceEngine.check() before store/embed/schema.
- **Documented limitations:** UNIFIED_ARCHITECTURE, production_checklist, and this document state what is complete vs. incomplete.

---

## Appendix: Deep-Dive Q&A

### “How do you handle failures?”

- **Kafka down:** API can still ingest (events stored in Mongo directly when called synchronously). Async path via Kafka would fail; producer would need retry/backoff. *Current state: connection retries at startup; no explicit producer retry on publish failure documented.*
- **Worker restarts:** Kafka consumer commits offsets; on restart, it resumes from last committed offset. Idempotency keys in Redis prevent duplicate processing of already-handled events.
- **Idempotency:** `_get_event_idempotency_key` (event_id or trace_id or payload hash); `_check_idempotency` and `_mark_processed` use Redis with TTL (1 hour).
- **Backpressure:** Kafka consumer fetches messages; processing is synchronous per message. *No explicit backpressure or rate limiting documented; assume consumer keeps up or lag grows.*

### “How do you enforce multi-tenant isolation?”

- **JWT:** `request.state.user` carries `tenant_id`, `space_id`, `user_id`, `roles`. Set by auth middleware.
- **Tenant context:** `get_tenant_context(request)` and `get_effective_tenant_context` read from JWT; no fallback to “dev” when user exists. 401 if unauthenticated (in production); 403 if tenant/user missing.
- **All queries:** EventStore, RAGEngine, SchemaEngine, History, Tasks—all accept and filter by `tenant_id` (and often `space_id`, `user_id`). No cross-tenant reads without explicit admin role and `allow_cross_tenant_roles`.
- **OPA:** `tenant_check` in kirp.rego: `input.tenant_id == input.user_tenant_id` or `cross_tenant_grant`. `space_check` enforces space membership.
- **Kafka events:** Payload carries `tenant_id`, `space_id`, `user_id`; processor rejects events with invalid or missing `tenant_id`.

### “How does RAG actually work in this system?”

- **Indexing:** On ingest, content is embedded via OpenAI (`text-embedding-3-small`), stored in Qdrant with metadata (tenant_id, space_id, user_id, source, timestamp). BM25 index built per tenant from document cache.
- **Retrieval:** `RAGEngine.search()` does semantic search (Qdrant) scoped by tenant/space; hybrid with BM25 when enabled. Returns `RAGResponse` with results, context_text, confidence.
- **Ask flow:** `InsightAgent.ask()` calls `rag.search()` with tenant/space; if results empty, returns fallback (“I could not find anything in your current data”); otherwise, LLM summarizes context with system prompt restricting to provided context only.
- **Agent use:** Agents receive `rag_response` in context when invoked from pipeline. No agent calls RAG directly; context is passed in.

### “How would you harden this for production?”

- **Security:** Full security review; dependency audit (e.g. `pip audit`, Snyk); ensure no secrets in logs; validate CORS and JWT rotation.
- **Resilience:** Dead-letter queue for failed Kafka events; retry with exponential backoff; circuit breakers for external services (OpenAI, Qdrant).
- **Observability:** Grafana dashboards for Prometheus metrics; centralized logging (ELK, Loki); distributed tracing (OpenTelemetry) for full request flow.
- **Data:** MongoDB replica set; Postgres replication/backup; Qdrant snapshot strategy; validate restore procedures.
- **Scaling:** Load test API and workers; tune Kafka partitions and consumer count; connection pool sizing for Mongo, Postgres, Redis.
- **Operations:** Runbooks for common failures; alerting on error rates, latency, consumer lag; documented rollback procedure.

---

*Document generated from actual codebase scan. Assumptions and current vs. intended state labeled explicitly. No invented features.*
