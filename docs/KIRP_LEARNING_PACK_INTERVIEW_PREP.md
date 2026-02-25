# KIRP System — Learning Pack & Interview Prep

Structured file map for deep-dive architecture/system-design interview prep.  
**Use real paths below; focus on what to read and what interviewers may ask.**

---

## SECTION A — High-Level Architecture & Entry Points

**Directory / files:**
- **App entry:** `src/main.py` — FastAPI app, lifespan, lazy singletons (EventStore, RAG, SchemaEngine, Governance, Pipeline, AgentFramework), all router includes, CORS, global exception handler.
- **Config / env:** `src/core/config.py` — App config; `.env.example` — API, DB, OAuth, Twilio, LLM keys.
- **Routing:** Router registration is in `src/main.py` (lines ~637–690): `ws_notifications`, `governance`, `observability`, `whatsapp_os`, `brand`, `v1_auth`, `command`, `auth`, `events`, `agents`, `tenants`, `users`, `decisions`, `graph`, `audit_api`, `v1_domain`, `v1_rag`, `v1_history`, `v1_tasks`, `v1_ingestion`, `v1_reminders`, `v1_execute`, `v1_context`, `v1_connections`, `v1_graph`, `v1_tenants_spaces`, `v1_events`, `v1_users`, `v1_scenarios`, `v1_notifications`, `llm_usage_router`.
- **WebSocket:** `src/api/ws_notifications.py` — `/ws/notifications` endpoint.
- **Architecture docs:** `docs/KIRP_ARCHITECTURE.md`, `docs/ARCHITECTURE.md`, `docs/KIRP_MASTER_PLAN.md`, `docs/KIRP_AI_UPGRADE_PLAN.md`.

**Must-read files (60–90 min):**
- **`src/main.py`** — Single place that wires app, deps, and all HTTP/WS routes; understand lazy init and router order.
- **`src/core/config.py`** — How env drives backend behavior.
- **`docs/KIRP_ARCHITECTURE.md`** — Ingestion, EventPipeline, SchemaEngine, agents, execution, shared context, UI, Notion sync; vision vs gaps.

**Additional useful files:**
- `src/api/ws_notifications.py`
- `.env.example`
- `docs/ARCHITECTURE.md`

**Interview focus:**
- Why FastAPI + lazy singletons for EventStore/RAG/Schema? (startup vs first request, connection pooling.)
- How would you add a new API version without breaking v1? (router prefix, deprecation.)
- Where does tenant_id/user_id enter the request path? (JWT → request.state → TenantContext.)
- Toughest: Failure modes if Mongo/Postgres/Qdrant are down at startup vs mid-request; how to make pipeline steps independently retryable.

---

## SECTION B — Ingestion & Connectors

**Directory / files:**
- **Connectors:** `src/integrations/whatsapp.py`, `src/integrations/gmail.py`, `src/integrations/calendar.py`, `src/integrations/notion.py`, `src/integrations/slack.py`, `src/integrations/email.py`, `src/integrations/__init__.py`.
- **Webhook handlers:** `src/api/v1_ingestion.py` — `/api/v1/webhooks/slack`, `/webhooks/notion`, `/webhooks/whatsapp`; also `POST /gmail/sync`, `/calendar/sync`, `/slack/sync`.
- **Sync workers / helpers:** `src/workers/connector_sync.py` — `run_gmail_sync`, `run_calendar_sync`, `run_slack_sync`, `run_notion_sync`; idempotent ingest via `EventStore.find_by_external_id` + `EventPipeline.run`.
- **Unified format:** `docs/UNIFIED_INGESTION_FORMAT.md` — tenant_id, space_id, user_id, source, content, metadata.external_id.
- **Connections API:** `src/api/v1_connections.py` — list connections, connect/disconnect, sync, validate, errors; OAuth start/callback for Gmail, Calendar, Slack, Notion.
- **Sync state:** `src/core/connector_sync_log.py` — cursor storage (page_token, sync_token) per user/integration.

**Must-read files (60–90 min):**
- **`src/api/v1_ingestion.py`** — Webhooks normalize → Kafka emit only; sync endpoints call connector then pipeline; Notion signature verification and bi-directional flow.
- **`src/workers/connector_sync.py`** — Idempotent ingest loop: external_id check → pipeline.run; shared pattern for Gmail/Calendar/Slack/Notion.
- **`src/integrations/gmail.py`** and **`src/integrations/whatsapp.py`** — One pull-based (OAuth, cursors) and one push-based (Twilio webhook); contrast with Notion in v1_ingestion.
- **`docs/UNIFIED_INGESTION_FORMAT.md`** — Single contract for “external events → internal events.”

**Additional useful files:**
- `src/api/v1_connections.py` (OAuth flows, sync triggers)
- `src/integrations/notion.py`
- `src/core/connector_sync_log.py`

**Interview focus:**
- Why publish to Kafka from webhooks instead of calling the pipeline directly? (decoupling, backpressure, replay, durability.)
- How idempotency is guaranteed (external_id + source + tenant; Redis in Kafka processor).
- Gmail/Calendar incremental sync: where is cursor stored and how is it passed?
- Toughest: Notion bi-directional: conflict policy, ordering, and what happens if webhook and PATCH node race.

---

## SECTION C — Event Store, Pipelines & RAG

**Directory / files:**
- **EventStore:** `src/core/event_store.py` — Event dataclass, Sensitivity, MongoDB store, find_by_external_id, append, list.
- **Event pipeline:** `src/core/pipeline.py` — EventPipeline.run: governance → store → embed → Qdrant upsert → history → life_objects → SchemaEngine.upsert_node.
- **RAG:** `src/core/rag_engine.py` — RAGEngine: hybrid (semantic + BM25), multi-hop, tenant/space scoping, embed, upsert, search.
- **Event types / canonical:** `src/models/event.py` — CanonicalEvent, EVENT_TYPE_INGEST, EVENT_TYPE_AGENT_RUN, to_payload/from_payload.
- **Event registry:** `src/core/event_registry.py` — EventRegistry, register(ingest.v1, agent_run.v1), dispatch; `src/core/event_registry_handlers.py` — handle_ingest_v1 (pipeline.run), handle_agent_run_v1 (agent engine).
- **Kafka consumer:** `src/workers/kafka_processor.py` — Consumes kirp-events, idempotency (Redis), retries, calls EventRegistry.dispatch; metrics.
- **RAG API:** `src/api/v1_rag.py` — POST search/semantic; `src/core/llm_router.py` / `src/core/llm_client.py` — LLM routing for agents.

**Must-read files (60–90 min):**
- **`src/core/event_store.py`** — Event model, store interface, find_by_external_id; why MongoDB for events.
- **`src/core/pipeline.py`** — Full run() flow: governance → store → RAG → history → life_objects → schema; where failures are logged vs raised.
- **`src/core/rag_engine.py`** — Hybrid search, scoping, embed/upsert; how Qdrant is used.
- **`src/workers/kafka_processor.py`** — How events get from Kafka to EventRegistry and pipeline; idempotency key and retry policy.
- **`src/core/event_registry_handlers.py`** — Single place that maps ingest.v1 → pipeline, agent_run.v1 → agent execution.

**Additional useful files:**
- `src/models/event.py`
- `src/core/event_registry.py`
- `src/api/v1_rag.py`

**Interview focus:**
- Event-sourcing: why append-only events + derived state (schema, history)? Replay and debugging.
- Ordering guarantees: per-connector vs global; partition key choice for Kafka.
- RAG: why hybrid (semantic + BM25)? How tenant/space isolation is enforced in Qdrant and in code.
- Toughest: Pipeline partial failure (e.g. store succeeds, Qdrant fails): consistency, retries, and exactly-once semantics.

---

## SECTION D — SchemaEngine & Domain Models

**Directory / files:**
- **SchemaEngine:** `src/core/schema_engine.py` — get_schema_engine, list_nodes, get_node, upsert_node, list_upcoming_obligations, ensure_life_areas, cache invalidation.
- **Life objects:** `src/core/life_objects.py` — extract_life_objects (Task, Project, Commitment, LifeArea), parse_due_date (EN + HE), keyword classification.
- **Schema models:** `src/models/schema.py` — SchemaEntity (task, project, commitment, life_area, category), SchemaNode, LIFE_AREA_NAMES.
- **Migrations / DDL:** `deploy/postgres-init/01-init-db.sh` — DB init; schema is SQLAlchemy ORM (see `src/models/schema.py`, `src/models/base.py`).
- **Tasks/nodes API:** `src/api/v1_tasks.py` — GET/POST tasks, GET/PATCH/POST nodes; PATCH node with notion_page_id triggers execute_command(update_notion_task).

**Must-read files (60–90 min):**
- **`src/core/schema_engine.py`** — Session pattern, cache (list_nodes), conditions for list_nodes and list_upcoming_obligations; how pipeline calls upsert_node.
- **`src/core/life_objects.py`** — How raw content becomes structured entities and due dates; deterministic node_id (e.g. UUID5) for idempotency.
- **`src/models/schema.py`** — SchemaEntity, SchemaNode columns, life areas; how obligations are “tasks/commitments with due_date.”

**Additional useful files:**
- `src/api/v1_tasks.py`
- `deploy/postgres-init/01-init-db.sh`
- `src/models/base.py`

**Interview focus:**
- Why Postgres for schema and Mongo for events? (structured query vs append-only, different access patterns.)
- list_upcoming_obligations: who consumes it (ReminderAgent, UI) and how it affects reminders.
- Life-object extraction: rule-based vs LLM; handling Hebrew and multiple date formats.
- Toughest: Cache invalidation strategy when pipeline upserts nodes; consistency under concurrent writes.

---

## SECTION E — Agents & Orchestration

**Directory / files:**
- **Framework / registry:** `src/core/agent_framework.py` — AgentSpec, AutonomyLevel, AgentFramework (register, get, list_by_trigger, run); `src/core/agent_registry.py` — register_all_agents, get_agent_framework_with_all_agents.
- **Specs (Phase 5):** `src/core/agents/specs.py` — PHASE5_AGENT_SPECS: PlannerAgent, InsightAgentV2, ReminderAgentV2, ExecutionAgent, OverloadAgent, ConflictAgent, SuggestFiltersAgent; triggers and tools.
- **Legacy + other agents:** `src/agents/pattern_analyzer.py`, `src/agents/planner.py`, `src/agents/forecaster.py`, `src/agents/risk_opportunity.py`, `src/agents/insight.py`, `src/agents/schema_structure.py`, `src/agents/presentation.py`, `src/agents/meta_agent.py`, `src/agents/orchestrator.py`, `src/agents/kafka_event_agent.py`, `src/agents/future_obligations.py`, `src/agents/reminder_agent.py`; `src/core/agents/base.py`, `src/core/agents/planner_agent.py`, `src/core/agents/insight_agent_v2.py`, `src/core/agents/reminder_agent_v2.py`, `src/core/agents/execution_agent.py`, `src/core/agents/overload_agent.py`, `src/core/agents/conflict_agent.py`, `src/core/agents/suggest_filters_agent.py`.
- **Scheduling / logs:** `src/core/agent_scheduler.py` — AgentLogsStore (MongoDB); scheduled trigger wiring in Celery.
- **Actions & execution:** `src/core/agent_actions.py` — action types, AgentActionsStore, action_doc; ExecutionAgent consumes pending; `src/core/execution_engine.py` — execute_command (create_notion_task, update_notion_task, send_whatsapp, create_calendar_event, send_email, post_slack); audit to EventStore (event_type=execution).
- **Agent API:** `src/api/agents.py` — list agents, run by id; `src/api/command.py` — POST /command/execute (MetaAgent-style).
- **Agent engine:** `src/core/agent_engine.py` — AgentExecutionEngine (Redis queue), execute_run.

**Must-read files (60–90 min):**
- **`src/core/agent_framework.py`** — AgentSpec, triggers, autonomy; how run() is invoked.
- **`src/core/agent_registry.py`** — Which agents are registered and from where (legacy + PHASE5_AGENT_SPECS).
- **`src/core/agents/specs.py`** — Phase 5 agents, tools (schema, agent_actions, execution_engine), triggers (scheduled, manual, new_event).
- **`src/core/agent_actions.py`** — Action types and store; how ExecutionAgent gets pending actions.
- **`src/core/execution_engine.py`** — All command types and integrations; audit trail.

**Additional useful files:**
- `src/core/agents/execution_agent.py`
- `src/core/agents/reminder_agent_v2.py`
- `src/api/agents.py`
- `src/core/event_registry_handlers.py` (handle_agent_run_v1)

**Interview focus:**
- Why registration-based agents? (pluggable, trigger-based dispatch, testability.)
- Flow: ingest event → Kafka → pipeline (no direct agent call); agent_run events and manual / scheduled runs.
- ExecutionAgent: how actions are queued (agent writes to AgentActionsStore) and executed (execute_command); approval workflow in v1_execute.
- Toughest: Autonomy levels and governance (OPA); how would you add “all ExecutionAgent actions require approval” without changing every agent?

---

## SECTION F — History, Notifications & Shared Context

**Directory / files:**
- **History:** `src/core/history.py` — HistoryEntry, HISTORY_TYPES, HistoryStore (MongoDB); human-readable timeline; `src/api/v1_history.py` — GET /history.
- **Notifications:** `src/core/notifications.py` — Notification model, NOTIFICATION_TYPES, NotificationsStore; `src/api/v1_notifications.py` — list, unread-count, read-all, mark read; `src/api/ws_notifications.py` — WebSocket for live updates.
- **Context / spaces:** `src/auth/tenant_context.py` — TenantContext, get_tenant_context (request.state.user), SKIP_AUTH; `src/api/v1_context.py` — GET accessible-spaces, spaces, can-access; space membership used for RAG/schema scoping.
- **Reminder preferences:** Used by ReminderAgent; stored in MongoDB (reminder_preferences, reminder_sent).

**Must-read files (60–90 min):**
- **`src/core/history.py`** — What gets written as history (types, tenant/space/user); difference from raw event log.
- **`src/core/notifications.py`** — Notification types and store; who writes (reminder agent, execution, sync errors).
- **`src/api/ws_notifications.py`** — How WebSocket is authenticated and how unread count is pushed.
- **`src/auth/tenant_context.py`** — How tenant_id/space_id/user_id are set per request; dev/local bypass.

**Additional useful files:**
- `src/api/v1_history.py`
- `src/api/v1_notifications.py`
- `src/api/v1_context.py`

**Interview focus:**
- History vs EventStore: when do you write history vs event? (pipeline writes both; history is “human” summary.)
- Notifications: delivery channels (in-app, email, WhatsApp) and where they are triggered.
- Shared context: get_accessible_space_ids and how RAG/SchemaEngine use it for multi-tenant isolation.
- Toughest: WebSocket scaling (per-connection state, reconnection, and consistency with REST unread count).

---

## SECTION G — Frontend / Dashboard

**Directory / files:**
- **Entrypoints:** `app/layout.tsx` — Root layout, ThemeProvider, LLMUsageToolbar; `app/(dashboard)/layout.tsx` — AppShell (SideNav, TopBar, auth guard).
- **Key pages:** `app/(dashboard)/dashboard/page.tsx` — Stats, events, agents, insights, quick ingest, ask; `app/(dashboard)/second-brain/page.tsx`, `app/(dashboard)/second-brain/inbox/page.tsx`, `app/(dashboard)/second-brain/timeline/page.tsx`, `app/(dashboard)/second-brain/life-areas/page.tsx`, `app/(dashboard)/second-brain/graph/page.tsx`, `app/(dashboard)/second-brain/suggestions/page.tsx`; `app/(dashboard)/insights/page.tsx`; `app/(dashboard)/agents/page.tsx`; `app/(dashboard)/history/page.tsx`; `app/(dashboard)/notifications/page.tsx`; `app/(dashboard)/connections/page.tsx`; `app/(dashboard)/tasks/page.tsx`; `app/(dashboard)/settings/users-roles/page.tsx`; `app/(dashboard)/graph/page.tsx`, `app/(dashboard)/events/page.tsx`, `app/(dashboard)/observability/page.tsx`, `app/(dashboard)/governance/audit/page.tsx`; `app/login/page.tsx`, `app/signup/page.tsx`, `app/logout/page.tsx`.
- **Core components:** `components/layout/AppShell.tsx` — Auth guard, tenant sync, SideNav, TopBar; `components/navigation/SideNav.tsx`, `components/navigation/TopBar.tsx`; `components/notifications/NotificationBell.tsx`, `components/notifications/NotificationPanel.tsx`; `components/dashboard/ThinkPanel.tsx`; `components/LLMUsageToolbar.tsx`; shared UI: `components/ui/*`, `components/dashboard/DataTable`, `components/dashboard/PageSkeleton`, `components/feedback/ErrorState`, charts.
- **Stores/hooks:** `lib/stores/authStore.ts` — User, login/logout, loadUser; `lib/stores/tenantContextStore.ts` — tenantId, spaceId, userId (synced from auth); `lib/stores/notificationStore.ts`; `lib/hooks/useNotificationsWs.ts` — WebSocket for notifications; `lib/apiClient.ts` — All API calls, auth headers, BASE URL; `lib/constants.ts` — DEFAULT_TENANT_ID etc.

**Must-read files (60–90 min):**
- **`app/layout.tsx`** and **`app/(dashboard)/layout.tsx`** — How dashboard is wrapped and protected.
- **`components/layout/AppShell.tsx`** — Auth guard, tenant sync to store, navigation; single place for “who is logged in and which space.”
- **`app/(dashboard)/dashboard/page.tsx`** — Data loading (getStats, listEvents, listAgents, getInsightsV1), quick ingest, ask; tenant/space from stores.
- **`lib/apiClient.ts`** — Token handling, base URL, main API methods used by pages.
- **`lib/stores/authStore.ts`** and **`lib/stores/tenantContextStore.ts`** — How auth and tenant context flow into API calls.

**Additional useful files:**
- `app/(dashboard)/second-brain/inbox/page.tsx`
- `app/(dashboard)/tasks/page.tsx`
- `components/notifications/NotificationBell.tsx`
- `lib/hooks/useNotificationsWs.ts`

**Interview focus:**
- Why Next.js App Router and (dashboard) route group? (layout reuse, auth boundary.)
- How does the UI get tenant_id/space_id on every request? (authStore → tenantContextStore → apiClient headers or params.)
- Notifications: REST vs WebSocket (initial load vs live updates).
- Toughest: Handling 401/403 globally (refresh token, redirect to login) and avoiding flash of wrong-tenant data.

---

## SECTION H — Auth, Multi-Tenancy & Security

**Directory / files:**
- **Auth core:** `src/core/auth.py` — User, UserStore (MongoDB); `src/core/jwt_utils.py` — JWT create/verify, require_auth, require_role.
- **Auth API:** `src/api/v1_auth.py` — POST register/signup, login, GET me, POST refresh; `src/api/auth.py` — roles, check, assign-role.
- **Tenant engine:** `src/auth/tenants.py` — Tenant, Space, SpaceKind, TenantEngine (Postgres); `src/auth/tenant_context.py` — TenantContext, get_tenant_context (FastAPI dependency).
- **Permissions:** `src/api/permissions.py` — POST effective permissions; `lib/auth/permissions.ts` — client-side permission checks if any.
- **Connector tokens:** `src/core/connector_tokens.py` — ConnectorTokenStore (MongoDB), encrypt at rest via EncryptionEngine; `src/auth/encryption.py` — KIRP_ENCRYPTION_KEY.

**Must-read files (60–90 min):**
- **`src/auth/tenant_context.py`** — get_tenant_context from request.state.user; SKIP_AUTH/local behavior; never leak tenant.
- **`src/api/v1_auth.py`** — Register/login flow, JWT issuance, /me and refresh.
- **`src/auth/tenants.py`** — Tenant/Space model and TenantEngine; how spaces map to Postgres.
- **`src/core/connector_tokens.py`** — Where OAuth/API tokens live; encryption at rest.

**Additional useful files:**
- `src/core/auth.py` (UserStore)
- `src/core/jwt_utils.py`
- `src/auth/encryption.py`

**Interview focus:**
- How tenant_id is guaranteed on every API call (JWT → middleware → request.state → get_tenant_context).
- Why both Mongo (users) and Postgres (tenants, spaces, space_memberships)? (auth vs org structure.)
- Connector tokens: why encrypt at rest; key rotation impact.
- Toughest: Cross-tenant access: where is it explicitly denied and how would you add a “shared space” across tenants?

---

## SECTION I — Infra, Background Jobs & Config

**Directory / files:**
- **Docker:** `docker-compose.yml` — mongodb, postgres, redis, qdrant, zookeeper, kafka, api, worker, dashboard, opa, prometheus, grafana, etc.; `deploy/Dockerfile.qdrant`, `deploy/postgres-init/01-init-db.sh`.
- **Celery:** `src/workers/celery_app.py` — broker/backend (Redis), include tasks, task_routes (ingest, whatsapp, scheduled, agents); `src/workers/tasks.py` — ingest_task, gmail_sync_task, calendar_sync_task, run_reminders_now, agent_run_task, etc.
- **Kafka:** `src/workers/kafka_processor.py` — consumer loop, topic kirp-events; `src/core/integrations.py` — get_kafka_consumer, get_redis_async.
- **Env / providers:** `.env.example` — API_HOST, MONGO_URI, POSTGRES_URI, GOOGLE_*, TWILIO_*, OPENAI_API_KEY, GROQ_API_KEY, QDRANT_*, KAFKA_*, REDIS_URL, CELERY_*, OPA_URL, KIRP_ENCRYPTION_KEY, etc.
- **Deploy/docs:** `deploy/CANONICAL_PATHS.md`, `deploy/opa/policies/kirp.rego`, `deploy/opa/policies/POLICY_STRUCTURE.md`, `docs/production_checklist.md`.

**Must-read files (60–90 min):**
- **`docker-compose.yml`** — All services (mongo, postgres, redis, qdrant, kafka, api, worker, dashboard); ports and env passed to containers.
- **`src/workers/celery_app.py`** — Queues (ingest, whatsapp, scheduled, agents); which tasks go where.
- **`src/workers/tasks.py`** — ingest_task, sync tasks, run_reminders_now, agent_run_task; how they call pipeline/connectors/agents.
- **`.env.example`** — Map each major feature (Gmail, Calendar, WhatsApp, Notion, Slack, LLM, Qdrant, Kafka, Redis) to env vars.

**Additional useful files:**
- `src/workers/kafka_processor.py` (already in Section C)
- `src/core/integrations.py`
- `deploy/opa/policies/kirp.rego`

**Interview focus:**
- Why Celery and Kafka both? (Celery: scheduled jobs, request/response; Kafka: event stream, replay, multiple consumers.)
- Task routing: ingest vs agents vs scheduled; backpressure and queue depth.
- Toughest: Deployment order (DBs → Kafka → workers → API → dashboard) and what happens if Kafka is down at startup (consumer retry in kafka_processor).

---

## Read in this order if you have 2 hours

1. **`docs/KIRP_ARCHITECTURE.md`** — End-to-end mental model.
2. **`src/main.py`** — Entry points and wiring.
3. **`src/core/pipeline.py`** — Event flow from ingest to schema.
4. **`src/core/event_store.py`** — Event model and store.
5. **`src/workers/kafka_processor.py`** — How events enter the system.
6. **`src/api/v1_ingestion.py`** — Webhooks and sync → Kafka.
7. **`src/core/agent_registry.py`** + **`src/core/agents/specs.py`** — Which agents exist and how they’re triggered.
8. **`src/core/execution_engine.py`** + **`src/core/agent_actions.py`** — How agent outputs become actions and commands.
9. **`src/core/schema_engine.py`** + **`src/core/life_objects.py`** — How events become tasks/commitments.
10. **`src/auth/tenant_context.py`** + **`src/auth/tenants.py`** — Multi-tenancy and context.
11. **`components/layout/AppShell.tsx`** + **`lib/apiClient.ts`** — Dashboard auth and API usage.
12. **`docker-compose.yml`** + **`src/workers/celery_app.py`** — Infra and background jobs.

---

## Read in this order if you only have 30 minutes

1. **`docs/KIRP_ARCHITECTURE.md`** (sections 1–2: current state, pipeline, schema, agents, execution, shared context).
2. **`src/main.py`** (router includes and lazy deps).
3. **`src/core/pipeline.py`** — run() only.
4. **`src/core/event_registry_handlers.py`** — ingest.v1 and agent_run.v1 handlers.
5. **`src/core/agent_registry.py`** + **`src/core/agents/specs.py`** (first ~100 lines) — Agent list and Phase 5.
6. **`src/auth/tenant_context.py`** — get_tenant_context and SKIP_AUTH.
7. **`docker-compose.yml`** — Service list and env.

---

*Generated for KIRP interview prep. Paths are from the repo as scanned; adjust if files move.*
