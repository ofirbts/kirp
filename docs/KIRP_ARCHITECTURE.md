# KIRP Enterprise — Architecture Document

Internal CTO / architecture review. Based on the current codebase, configuration, and wiring as of the last verification pass.

---

## 1. Current State of the System

### Ingestion

KIRP ingests from five source types that are wired and functioning: WhatsApp (Twilio webhook), Gmail (OAuth pull), Google Calendar (OAuth pull), Notion (OAuth/API key pull plus webhooks), and Slack (OAuth/bot token pull). Email is supported as a connector type in the Connections API but is not fully wired as a distinct inbound source in the same way as Gmail.

Data enters in two ways. Webhooks receive real-time payloads: WhatsApp via POST to `/api/v1/webhooks/whatsapp` (Twilio form-urlencoded, signature-validated); Notion via POST to `/api/v1/webhooks/notion` (JSON, X-Notion-Signature); Slack via POST to `/api/v1/webhooks/slack`. Each webhook normalizes the payload to a unified shape (tenant_id, space_id, user_id, source, content, metadata with external_id) and either publishes to Kafka (ingest flow) or, in the case of direct sync endpoints, runs the pipeline. Pull-based sync is triggered manually from the Connections UI or by calling POST `/api/v1/connections/{integration}/sync` (and equivalently POST `/api/v1/gmail/sync`, `/calendar/sync`, `/slack/sync`). Gmail and Calendar support per-user cursors: page_token (Gmail) and sync_token (Calendar) are stored in ConnectorSyncLogStore.last_sync_result and passed on the next sync for incremental behaviour. Sync frequency is therefore on-demand unless a separate scheduler (e.g. Celery) is configured to call these endpoints periodically.

Ingestion is robust where idempotency is enforced: every connector supplies metadata.external_id (message id, event id, page id, or Slack ts). EventStore.find_by_external_id is used before pipeline.run(), and the Kafka processor also checks idempotency (Redis key from event id or trace id) and skips duplicates. WhatsApp is robust in production once Twilio webhook URL and signature validation (including X-Forwarded-Host/Proto behind ngrok) are correct and WHATSAPP_WEBHOOK_TENANT_ID/USER_ID are set so events land in the right tenant and user. Notion and Slack sync depend on correct OAuth or token setup; Notion webhook requires a publicly reachable URL and NOTION_WEBHOOK_SECRET. The ingestion path that goes through Kafka is the canonical one; the system is built so that all normalized events flow through EventPipeline.

### EventPipeline

Raw inputs are normalized into canonical events before they reach the pipeline. Each connector or webhook handler produces a payload with tenant_id, space_id, user_id, source, content, and metadata (including external_id). That payload is either sent to Kafka (type "ingest") or passed directly to EventPipeline.run(). The pipeline does not re-normalize; it assumes the caller has already set tenant_id, space_id, user_id, source, content, and metadata.

Metadata is handled consistently. tenant_id and user_id are required for multi-tenant isolation; space_id defaults to "all" when not provided. source identifies the origin (gmail, calendar, notion, slack, whatsapp, email, webhook, api). external_id lives in metadata and is used for idempotency and for Notion bi-directional sync (notion_page_id). trace_id is set or preserved in metadata for debugging. The pipeline creates an Event with this metadata, runs a governance check, stores the event in MongoDB, embeds content via the RAG engine, upserts the vector in Qdrant, records a history entry, and then runs life-object extraction and SchemaEngine.upsert_node.

Guarantees today are: (1) idempotency at ingest via external_id + source in EventStore and at Kafka via idempotency keys in Redis; (2) ordering only insofar as Kafka or the sync worker processes one event at a time per logical stream—there is no strong ordering guarantee across connectors; (3) error handling: pipeline failures are logged and the event may already be stored before RAG or schema steps; RAG and life-object steps are best-effort (exceptions logged, pipeline still returns the event id). Governance rejections raise and prevent storage.

### SchemaEngine

The schema layer is implemented in PostgreSQL with a single table, schema_nodes, and an enum SchemaEntity: task, project, commitment, life_area, category. Canonical life areas (Work, Family, Health, Learning) are created per tenant/space via ensure_life_areas. Nodes have tenant_id, space_id, entity, title, description, parent_id, status, priority, due_date, and a JSON extra field used for metadata (source_event_id, source, notion_page_id, context, owner, etc.). There is no separate "obligations" table; obligations are a view over tasks and commitments that have a due_date, exposed via list_upcoming_obligations(tenant_id, space_id, due_from, due_to).

Events are transformed into structured entities inside EventPipeline. After an event is stored and embedded, extract_life_objects (in life_objects.py) classifies content into Task, Project, Commitment, or LifeArea using keyword rules and extracts a due date via parse_due_date (English and Hebrew NLP). Each extracted object is upserted into SchemaEngine with a stable node_id (UUID5 of event id and entity:title), source_event_id, and optional context and notion_page_id. So a single ingest event can create or update one or more schema nodes; the same event will not create duplicates because of the deterministic node_id.

This layer is stable for CRUD and for list_upcoming_obligations. The main evolution is in life_objects (classification and date parsing) and in how agents or future features attach more metadata or relationships. SchemaEngine is used by the pipeline, by agents (Planner, Reminder, Overload, Conflict, SuggestFilters, etc.), and by the UI (tasks, nodes, graph, obligations).

### Agents

The agent framework is registration-based. AgentFramework holds a list of AgentSpecs; each spec has a name, type, triggers (e.g. scheduled, manual, new_event), tools, autonomy level, and a handler function. register_all_agents in agent_registry.py wires: PatternAnalyzerAgent, TodayTomorrowPlannerAgent (planner_spec), ForecasterAgent, RiskOpportunityAgent, SchemaStructureAgent, PresentationAgent, SelfImprovementAgent, MetaAgent, FutureObligationsAgent, ReminderAgent, and the PHASE5_AGENT_SPECS (PlannerAgent, InsightAgentV2, ReminderAgentV2, ExecutionAgent, OverloadAgent, ConflictAgent, SuggestFiltersAgent). Agents are invoked by the Kafka processor (for ingest-triggered or agent_run events), by the API POST /api/agents/{agent_id}/run, by the AgentScheduler (scheduled trigger), or by the MetaAgent when it routes a user query.

In production flows, the pipeline does not directly trigger agents after ingest; the Kafka processor runs the pipeline for ingest events and can run agent_run events when such messages are present. ReminderAgent and ReminderAgentV2 are used by the reminders run endpoint and by Celery (run_reminders_now task) to deliver reminders. FutureObligationsAgent is used by ReminderAgent and by the UI /api/v1/reminders/upcoming. PlannerAgent and InsightAgentV2 are used when the user runs agents manually or when scenarios run. ExecutionAgent consumes queued actions from the agent_actions store. PatternAnalyzer, Forecaster, RiskOpportunity, SchemaStructure, Presentation, and SelfImprovement are registered and callable but are not part of the default ingest or reminder loop; they are used in scenarios or manual runs. MetaAgent is the entry point for natural-language command execution (e.g. /command/execute).

Agents interact with EventPipeline only indirectly: the pipeline writes to EventStore and SchemaEngine; agents read from EventStore (via RAG or direct list), from SchemaEngine (list_nodes, list_upcoming_obligations), and from RAG (semantic search). ExecutionAgent and the execution layer perform outbound actions (Notion, WhatsApp, Calendar, Email, Slack). The pipeline does not call agents; the Kafka processor can run both pipeline and agents depending on message type.

### Execution

Actions are executed through execute_command in the execution_engine. Supported command types are: create_notion_task, update_notion_task, send_whatsapp, create_calendar_event, send_email, post_slack. Each command loads the relevant integration (Notion, WhatsApp, Calendar, Email, Slack), uses tenant_id and user_id for context, and performs the operation. For example, update_notion_task reads the schema node to get notion_page_id and then calls NotionIntegration.update_page. All executions are audited by writing an event to EventStore with event_type "execution" and metadata containing command_type, payload, and result.

The API exposes POST /api/v1/execute with an optional approval workflow: requests can create a pending execution record; POST /execute/approve/{pending_id} and POST /execute/reject/{pending_id} complete the flow. The command executor is used by the ExecutionAgent (which reads from agent_actions and calls execute_command) and by the PATCH /api/v1/nodes/{node_id} flow when the updated node has notion_page_id (PATCH back to Notion).

Errors are handled inside execute_command with try/except; failures set result.ok to False and result.error to the message. There is no automatic retry in the execution engine; callers (e.g. Celery or the API) would need to implement retries. The audit log ensures every attempt is recorded.

### Shared Context

Shared user and tenant context is stored in several places. (1) MongoDB: events (event store), history (human-readable timeline entries per source), reminder_preferences (lead_hours, channels, quiet hours per user), reminder_sent (to avoid duplicate reminders), notifications (in-app), connector_sync_log (per user/integration), and agent_actions (queued actions). (2) PostgreSQL: schema_nodes (tasks, projects, commitments, life areas), space_memberships (user_id, space_id, tenant_id, role), tenants and spaces. (3) Context service: get_accessible_space_ids(tenant_id, user_id) and list_spaces_for_context return the list of space_ids a user can access based on SpaceMembership, so that RAG and schema queries can be scoped correctly.

Agents and the UI read this context via the same APIs: list_upcoming_obligations (schema), list history (history API), get reminder preferences, list notifications, list_events. Agents that need RAG call the RAG engine with tenant_id and space_id; the engine scopes Qdrant and in-memory filters by those. Writing is done by the pipeline (events, history, schema nodes), by the reminder agent (reminder_sent, notification events), by the execution engine (execution events), and by the UI (e.g. updating nodes, preferences, read state). Consistency is eventual: there is no single transaction across Mongo and Postgres; the design assumes that the event store is the source of truth for raw events and that schema and history are derived or updated asynchronously.

### UI

The dashboard is a Next.js app under app/(dashboard). The main surfaces are: dashboard (stats, recent events, agents list, insights, quick ingest, ask); second-brain (inbox, timeline, life-areas, tasks, graph, suggestions); connections (list connectors, connect/disconnect, sync, validate, errors); tasks (list tasks/nodes from SchemaEngine, create, update); reminders (upcoming obligations, preferences, run reminders); notifications (list, unread count, mark read); history (list history with filters); insights; agents (list agents, run agent); graph (knowledge graph from SchemaEngine + EventStore); settings (users/roles); observability (metrics, health); governance (audit, approvals); and additional pages for events, signals, visuals, content, decisions, tenants, pipeline, run, dev, mission-control, system-control, think.

The dashboard page loads real data: getStats, listEvents, listAgents, getInsightsV1. The second-brain inbox loads listEvents (tenant/space scoped) and shows recent ingested items with source and timestamp. Tasks and nodes are backed by GET /api/v1/tasks and /api/v1/nodes. Timeline and obligations are backed by history and reminders/upcoming. The graph page uses GET /api/v1/graph. Notifications use the notifications API and WebSocket for live unread count. Parts that are still placeholder or thin: some observability and governance screens may show minimal data if backend endpoints return empty or stub data; workflow and task-retry APIs exist but may not be fully wired to engines. The core second-brain flows (inbox, tasks, timeline, obligations, graph) and connections management are backed by real APIs and are production-ready for daily use.

### Notion Sync (and similar content sync)

Notion is the only content sync implemented in a bi-directional way. Pull: run_notion_sync (or Connections sync for Notion) uses NotionIntegration.ingest_database to fetch database pages, then for each page checks EventStore.find_by_external_id(notion, page_id); if not found, runs the pipeline. So new pages are ingested as events and then as schema nodes (with notion_page_id in metadata). Webhooks: POST /api/v1/webhooks/notion receives Notion events, verifies X-Notion-Signature, re-fetches the page via fetch_page, and emits an ingest envelope to Kafka with external_id; the Kafka processor either updates by external_id and runs post_ingest (re-embed and re-run life objects) or runs the full pipeline for new events. PATCH back: when a user updates a node in the UI (PATCH /api/v1/nodes/{node_id}) and the node has metadata.notion_page_id, the API calls execute_command(update_notion_task, ...), which updates the Notion page title/status/due. So the directions are: Notion → KIRP (scheduled pull and webhook), KIRP → Notion (node update from UI). There is no separate conflict policy beyond "last write wins" (Notion webhook overwrites our event; our PATCH overwrites Notion). Notion sync is production-ready for the implemented flows; multi-user or multi-workspace Notion would require additional tenant/user mapping.

No other content sync (e.g. another CRM or docs provider) is implemented in the same bi-directional way in the repo.

---

## 2. Vision Gap Analysis

### The vision of KIRP as an "Ultimate Second Brain"

An Ultimate Second Brain would provide a single place where everything that matters to the user is captured, organized, and actionable. That implies: durable memory (events, tasks, commitments, and their relationships); reasoning over that memory (patterns, risks, opportunities, summaries); planning (daily and weekly plans, priorities, and suggestions); clear obligations (what is due, when, and from which source); proactive help (reminders, nudges, and recommendations without being asked); and a unified view across life and work (one timeline, one graph, one inbox). The system would feel like an extension of the user’s mind: it would know what they care about, what they committed to, and what is coming next.

### What already aligns with this vision today

KIRP already has multi-source ingestion (WhatsApp, Gmail, Calendar, Notion, Slack) into a single event store and a single schema layer, so one timeline and one task/commitment graph are possible. Obligations are explicitly modeled: tasks and commitments with due_date are queried via list_upcoming_obligations and drive the reminders API and the ReminderAgent. The pipeline turns raw events into structured tasks, projects, and commitments with NLP for due dates (including Hebrew). The RAG engine and InsightsEngine use that data to produce workload summaries, patterns, and recommendations. The dashboard and second-brain UI expose inbox, timeline, tasks, graph, and insights, so the user can see a unified view. Reminders can be delivered via email, WhatsApp, or in-app notification based on user preferences. So the foundation for a second brain—capture, structure, obligations, reminders, and a single pane of glass—is in place.

### What is still missing

The system does not yet feel fully "proactive" or "always on." Scheduled agents depend on a running scheduler (e.g. AgentScheduler or Celery); if nothing calls them, reminders and insights do not run on their own. There is no single "daily brief" or "morning digest" that aggregates obligations, calendar, and insights into one push. Coverage of life domains is partial: life areas exist as schema and filters, but the UX does not strongly guide the user to tag or view by Work/Family/Health/Learning everywhere. Multi-modal context (e.g. images, voice, or rich documents) is not first-class; ingestion is text-oriented. The quality of insights and recommendations depends on how much data has been ingested and on the InsightsEngine logic; there is no strong feedback loop yet to tune "what matters" per user. UX coherence varies: some screens are dense or technical (e.g. observability, pipeline); the transition from "inbox" to "what should I do today" could be clearer.

### Key gaps between current state and target

**Reliability and operability.** Ingestion and pipeline are robust when services (Mongo, Postgres, Qdrant, Redis, Kafka) are up and correctly configured; there is no full self-test or chaos-resistant design. Scheduled sync and reminders require explicit deployment of workers and schedulers. Observability (metrics, alerts, health) exists but is not yet a single pane for "is my second brain healthy."

**Coverage of life domains and sources.** More sources (e.g. more calendars, notes apps, or communication tools) would increase the completeness of the brain. Life areas are modeled but underused in filtering and recommendations. There is no deep integration with a calendar as the "source of truth" for time (e.g. blocking time for tasks).

**Proactive workflows.** Today the user must open the app or trigger sync/reminders. A true second brain would push a daily brief, nudge before deadlines, and surface "you have a free slot, here are top tasks" without the user asking. That requires reliable scheduling, delivery channels, and possibly a dedicated "briefing" agent.

**Insight richness and personalization.** InsightsEngine produces workload, pattern, commitment, and recommendation insights from schema and events. The logic is rule- and heuristic-based; there is no learning from user feedback (e.g. "dismiss" or "useful"). RAG supports semantic search but is not yet the primary driver of "what should I focus on" in a personalized way.

**Integrations depth.** Each connector does the minimum: ingest (and for Notion, PATCH back). There is no two-way sync for Gmail (e.g. mark as read, send), Calendar (accept/decline, move), or Slack (threads, reactions). Deeper integration would make the second brain feel more connected to the tools the user already uses.

**UX coherence.** The dashboard has many entry points (dashboard, second brain, tasks, graph, insights, agents, history, settings). A clearer "home" that answers "what’s now, what’s next, what matters" would reduce cognitive load and make the system feel more like a single brain rather than a collection of tools.

---

## 3. Full Agent Mapping

**PatternAnalyzerAgent.** Conceptually detects habits, overload, procrastination, and repeated themes in the user’s activity. Inputs: events and/or schema (tasks, commitments), typically fetched via RAG or event store listing; can be triggered by scheduled or manual runs. Outputs: insights (e.g. patterns, overload signals). Reactive to data scans; can be run proactively on a schedule. Dependencies: RAG/EventStore for content; SchemaEngine for tasks/commitments if used.

**TodayTomorrowPlannerAgent (planner_spec).** Builds daily and weekly plans and identifies critical actions. Inputs: context (query, tenant_id, space_id, user_id), and typically tasks/commitments/obligations from SchemaEngine or RAG. Outputs: plan-like structure (e.g. today/tomorrow actions, priorities). Reactive when invoked with a query; can be scheduled. Dependencies: SchemaEngine (or RAG) for tasks and commitments.

**ForecasterAgent.** Predicts tomorrow’s load, bottlenecks, and upcoming issues. Inputs: historical or current events/tasks (from store or schema). Outputs: forecast insights. Predictive in nature. Dependencies: EventStore and/or SchemaEngine.

**RiskOpportunityAgent.** Detects risks, missed follow-ups, and emerging opportunities. Inputs: events, tasks, commitments (from RAG or schema). Outputs: risk/opportunity insights. Reactive/proactive. Dependencies: RAG, SchemaEngine.

**SchemaStructureAgent.** Builds or refines schemas: tasks, projects, life areas, categories. Inputs: raw or structured content (e.g. from events or LLM). Outputs: schema node create/update suggestions or direct writes. Reactive when invoked. Dependencies: SchemaEngine for writes.

**PresentationAgent.** Generates live views: Kanban, Timeline, Calendar, Mind Map. Inputs: schema nodes and/or events. Outputs: structured payloads for UI (e.g. lanes, time buckets). Reactive. Dependencies: SchemaEngine, possibly EventStore.

**SelfImprovementAgent.** Learns from logs and aims to improve prompts, agents, and pipelines. Inputs: logs or run history. Outputs: suggestions or internal updates. Experimental; reactive or batch. Dependencies: internal logs/store.

**MetaAgent.** Orchestrates other agents and routes user queries to the best agent. Inputs: user query (e.g. from /command/execute), tenant/space/user. Outputs: delegated result from another agent. Reactive. Dependencies: AgentFramework (other agents), SchemaEngine, RAG as used by child agents.

**FutureObligationsAgent.** Lists upcoming tasks and commitments with due_date in a time window. Inputs: tenant_id, space_id, user_id, context (e.g. horizon_days). Outputs: list of obligations with metadata (owner, due_date, etc.). Reactive when called; used by ReminderAgent and by the UI. Dependencies: SchemaEngine (list_upcoming_obligations).

**ReminderAgent.** Schedules and delivers reminders for upcoming obligations. Inputs: obligations (from SchemaEngine or FutureObligationsAgent), user reminder preferences (lead time, channels). Outputs: sent reminders (email, WhatsApp, or in-app notification) and tracking to avoid duplicates. Proactive when run on a schedule (e.g. Celery). Dependencies: SchemaEngine, ReminderPreferencesStore, ReminderSentStore, Email/WhatsApp integrations, EventStore for notification events.

**PlannerAgent (PHASE5).** Produces daily plan, weekly plan, and suggested priorities from tasks and commitments. Inputs: tenant_id, space_id, user_id, context. Outputs: priorities, plan summary. Reactive/proactive. Dependencies: SchemaEngine (list_nodes, list_upcoming_obligations).

**InsightAgentV2.** Provides deeper insights and cross-entity reasoning using InsightsEngine and the life graph. Inputs: tenant_id, space_id, user_id. Outputs: insights (workload, patterns, commitments, recommendations). Reactive/proactive. Dependencies: SchemaEngine, EventStore, InsightsEngine.

**ReminderAgentV2.** Detects upcoming deadlines and overdue items and suggests reschedule. Inputs: obligations from SchemaEngine. Outputs: insights (overdue, due soon) and possibly suggested actions. Proactive/reactive. Dependencies: SchemaEngine.

**ExecutionAgent.** Executes queued actions: create_task, update_task, send_notification, send_message. Inputs: agent_actions store (pending actions). Outputs: side effects via execution_engine (Notion, WhatsApp, Calendar, Email, Slack) and audit events. Reactive (triggered when actions are queued). Dependencies: Execution engine, SchemaEngine (for node updates), integrations.

**OverloadAgent.** Detects workload overload, too many active projects, and too many commitments. Inputs: schema nodes (tasks, projects, commitments). Outputs: insights (e.g. high task load, many projects). Proactive/reactive. Dependencies: SchemaEngine, optionally graph.

**ConflictAgent.** Detects schedule conflicts, double-bookings, and impossible deadlines. Inputs: tasks/commitments with due dates. Outputs: conflict insights. Reactive/proactive. Dependencies: SchemaEngine.

**SuggestFiltersAgent.** Detects noise and suggests grouping or filters for inbox and task views. Inputs: schema nodes (tasks) and their sources. Outputs: suggestions (e.g. group by source, filter pending). Reactive/proactive. Dependencies: SchemaEngine.

---

## 4. Pipeline Mapping

**Ingestion to Event Store.** When a WhatsApp message arrives, Twilio POSTs to the webhook; the handler parses the body, validates the Twilio signature (using the request URL reconstructed from X-Forwarded-Host/Proto when behind a proxy), resolves tenant_id and user_id from env (WHATSAPP_WEBHOOK_TENANT_ID, WHATSAPP_WEBHOOK_USER_ID) or defaults, normalizes to a unified payload (content, source=whatsapp, metadata including external_id from message id), and emits to Kafka (type "ingest"). Gmail/Calendar/Notion/Slack sync paths either emit to Kafka or call the pipeline directly with the same payload shape. The Kafka consumer reads from kirp-events, checks idempotency (Redis key from event id or trace id), and for ingest messages loads EventStore, RAG, SchemaEngine, Governance, and EventPipeline, then calls pipeline.run() with the payload’s tenant_id, space_id, user_id, source, content, metadata. The pipeline runs governance, creates an Event, stores it in MongoDB, and returns. Deduplication is ensured by (1) connector sync checking find_by_external_id before calling the pipeline and (2) Kafka processor checking idempotency and, for existing external_id, optionally calling update_by_external_id and run_post_ingest instead of a full new run.

**Event Store to Embeddings to Qdrant (RAG).** Inside the same pipeline.run(), after the event is stored, the pipeline calls the RAG engine to embed the content (using the configured embedding provider and model, e.g. OpenAI text-embedding-3-small) and upserts one point into Qdrant with the event id, embedding, content, source, tenant_id, space_id, user_id, timestamp, and trace_id. So every ingested event that passes the pipeline gets one vector. Tenant/space/user scoping is stored in the point payload and used at query time so that RAG search only returns points matching the request’s tenant and space. Events are selected for embedding by the fact that they go through the pipeline; there is no separate "selection" step. Failed embed or upsert are logged but do not fail the pipeline.

**Qdrant to Agents.** Agents that need context call the RAG engine (e.g. search or hybrid search) with a query string and tenant_id/space_id. The engine embeds the query, searches Qdrant with filters, and optionally runs BM25 or multi-hop; results are returned as RetrievalResult list with text, score, source, metadata. Typical use is "recent activity and upcoming obligations" or a user question; the agent then uses this context plus schema data (list_nodes, list_upcoming_obligations) to produce insights or plans. There is no single "agent query" pipeline; each agent that uses RAG does so when its handler runs.

**Agents to SchemaEngine.** The pipeline itself, not a separate agent, turns raw events into schema nodes. After storing the event and upserting to Qdrant, the pipeline calls extract_life_objects on the event content, then for each object calls schema.upsert_node with entity, title, due_date, metadata (source_event_id, source, context, notion_page_id when applicable). Agents that create or update tasks (e.g. ExecutionAgent) call schema.create_node or schema.update_node. Updates are written in the same PostgreSQL schema_nodes table; consistency is per-request (no cross-request transactions). The pipeline uses a deterministic node_id (UUID5 of event id and "entity:title") so the same event does not create duplicate nodes.

**SchemaEngine to UI.** Structured data reaches the UI through REST. GET /api/v1/tasks and GET /api/v1/nodes return schema nodes (filtered by tenant/space). GET /api/v1/reminders/upcoming returns list_upcoming_obligations. GET /api/v1/graph returns the knowledge graph (nodes and edges from SchemaEngine and EventStore). GET /api/v1/history returns history entries. GET /api/v1/notifications returns notifications; WebSocket can push unread count. The dashboard page calls getStats, listEvents, listAgents, getInsightsV1; the second-brain inbox calls listEvents; tasks page calls the task/node APIs; timeline and obligations use history and reminders. So the flow is: SchemaEngine (and EventStore, history, notifications) → REST (and WebSocket) → React state → screens.

**Other pipelines.** Notion sync: pull runs notion.ingest_database, then for each page either skips (existing external_id) or pipeline.run(); webhook receives Notion events, fetches page, emits ingest to Kafka (or updates by external_id and post_ingest); UI PATCH on a node with notion_page_id triggers execute_command(update_notion_task). Execution workflow: user or agent creates a pending execution; approve or reject endpoints call the execution engine and clear the pending record. Reminders: Celery task or POST /reminders/run loads obligations, applies user preferences (lead time, channels), and for each due reminder calls ReminderAgent delivery (email, WhatsApp, or notification event); ReminderSentStore prevents duplicates.

---

## 5. Mapping of Newly Built Capabilities

**Connectors.** WhatsApp: receive via Twilio webhook, validate signature, normalize to ingest; send via Twilio (from_ from TWILIO_NUMBER). Gmail: OAuth with refresh, list_messages with optional page_token (cursor stored in sync log), normalize to ingest; no send. Calendar: OAuth with refresh, list_events (7 days back + future) with optional sync_token (cursor stored); create_event for execution; no two-way sync of accept/decline. Notion: OAuth or API key, ingest_database and fetch_page, webhook for updates, create_task and update_page for execution; PATCH from UI when node has notion_page_id. Slack: OAuth/bot, fetch_recent_messages (with cursor), normalize to ingest; post_message for execution. Email: connector type exists in Connections; send implemented in execution; inbound as a distinct source is not fully wired like Gmail. Maturity: WhatsApp, Gmail, Calendar, Notion are production-ready for the described flows; Slack depends on token and channel config.

**NLP / LLM layer.** LLMs are used for: embeddings (RAG) via the configured provider (e.g. OpenAI text-embedding-3-small); optional use in agents (e.g. summarization, planning) where agents call LLM APIs. RAG is the primary consumer of embeddings; reasoning agents (Planner, Insight, Meta) may use LLM for text generation. Provider and model are configured via env (OPENAI_API_KEY, GROQ_API_KEY, EMBEDDING_PROVIDER, EMBEDDING_MODEL). Pattern analysis and date extraction in life_objects are rule-based (including Hebrew phrases: מחר בבוקר, שבוע הבא, יום שלישי בערב, etc.); no LLM is required for classification or parse_due_date.

**Obligations.** Obligations are tasks and commitments in SchemaEngine that have a non-null due_date. They are derived from events by the pipeline (extract_life_objects sets due_date from parse_due_date and classifies Commitment vs Task) and from manual or API-created nodes. list_upcoming_obligations(tenant_id, space_id, due_from, due_to) returns them; there is no separate obligation table. They feed the reminders API (GET /reminders/upcoming), ReminderAgent/ReminderAgentV2, PlannerAgent, and the second-brain timeline/obligation views.

**Reminders.** Reminder logic: ReminderPreferencesStore holds per-user lead_hours, channels (email, whatsapp, notification), and optional quiet hours. ReminderSentStore records which (node_id, due) have already been sent. When reminders run (POST /reminders/run or Celery run_reminders_now), the agent loads obligations in the horizon, filters by "reminder time has passed" (due - lead_hours), and for each unsent obligation delivers via the chosen channel(s) and marks sent. Channels: email (EmailIntegration), WhatsApp (WhatsAppIntegration), notification (EventStore ingest with event_type reminder; UI shows in notifications). No retry logic in the agent; failures are logged.

**Execution.** Real capabilities: create_notion_task, update_notion_task (NotionIntegration); send_whatsapp (Twilio); create_calendar_event (Google Calendar); send_email; post_slack. Each is implemented and audited. Guardrails: governance can gate writes; execution API can require approval (pending → approve/reject). Reliability: single attempt per call; no built-in retry.

**Shared context.** Long-term context is built from: EventStore (raw events), history (human-readable timeline), schema_nodes (tasks, projects, commitments, life areas), reminder_preferences and reminder_sent, notifications, and space_memberships. Agents and UI read via the same APIs; agents that need "what can this user see" use get_accessible_space_ids or list_spaces_for_context so RAG and schema queries are scoped. Consistency is eventual; no cross-store transactions.

**UI.** New or repaired surfaces: dashboard (stats, events, agents, insights, quick ingest, ask); second-brain (inbox with auto-refresh, timeline, life-areas, tasks, graph, suggestions); connections (list, connect, disconnect, sync with cursor support, validate, errors); tasks (list, create, update, including Notion PATCH when node has notion_page_id); reminders (upcoming obligations, preferences, run); notifications (list, unread count, mark read, WebSocket); history (list with filters); graph (v1 graph API); observability (metrics, health); governance (audit, approvals). Production-ready: dashboard, second-brain inbox and tasks, connections, reminders, notifications, history. Still rough or partial: some observability and governance screens, workflow/task-retry UX.

**Notion sync.** End-to-end: (1) Pull: sync fetches pages, dedupes by external_id, runs pipeline for new pages. (2) Webhook: Notion sends event, we verify signature, fetch page, emit ingest (or update by external_id + run_post_ingest). (3) PATCH back: UI updates a node → if notion_page_id present, execute_command(update_notion_task) updates the Notion page. Partial: no conflict resolution policy beyond last-write-wins; no full sync "diff" or batch PATCH. Planned or suggested in docs: not specified beyond current implementation.

---

## 6. Next Steps (Concrete Options)

### a. Product

**Daily brief.** Introduce a single "daily brief" or "morning digest" that aggregates today’s obligations, calendar events, and top insights into one payload and deliver it via the user’s preferred channel (email or WhatsApp) at a configurable time. This would make the second brain feel proactive and would reuse existing obligations, calendar, and InsightsEngine.

**Richer insights and recommendations.** Extend InsightsEngine (or a dedicated agent) to produce more personalized recommendations (e.g. "focus on X because of deadline Y" or "you have a free slot, here are top tasks") and optionally consume user feedback (dismiss, mark useful) to improve relevance over time.

**Cross-source inbox and "what’s next".** Unify the inbox view so that WhatsApp, Gmail, Calendar, Notion, and Slack items appear in one ordered stream with clear source labels and actions (e.g. "snooze," "convert to task"). Add a dedicated "what’s next" view that surfaces the next few obligations and calendar items in one place.

**Life-area emphasis.** Use life areas (Work, Family, Health, Learning) more prominently in filters, insights, and recommendations so the user can switch context by domain and the system can balance or suggest across domains.

### b. AI / Agents

**Scheduled agent runs and reminder reliability.** Ensure a single, documented path for "scheduled" agents (e.g. Celery beat or a dedicated scheduler service) so that ReminderAgent, InsightAgentV2, and PlannerAgent run on a cadence without manual trigger. This closes the gap between "agents exist" and "agents run automatically."

**Briefing agent.** Add an agent that, when run (e.g. daily), calls FutureObligationsAgent, calendar (if available), and InsightsEngine, formats a brief, and triggers delivery via the execution layer (email or WhatsApp). This is the main leverage point for proactive value.

**Agent coordination and MetaAgent.** Strengthen MetaAgent so that natural-language commands (e.g. "what should I do today," "remind me about X") are reliably routed to the right agent and the result is returned in a consistent format. This improves the "ask the brain" experience.

**Feedback loop for insights.** Allow the UI to send feedback (e.g. "not useful," "useful") for insights and store it; use it to tune ranking or to train a simple model so that recommendations improve over time.

### c. UX

**Single "home" for "now and next".** Redesign the dashboard or add a clear "home" tab that answers: what’s due today, what’s on the calendar, what’s the next recommended action, and one or two top insights. This reduces fragmentation and makes the system feel like one place.

**Timeline and obligations in one view.** Combine timeline (history) and upcoming obligations into one chronological or priority-ordered view so the user sees "what happened" and "what’s due" together without switching screens.

**Connections and sync status.** Surface sync status and last error per connector more prominently (e.g. on the second-brain or dashboard) and offer one-click "sync now" or "fix" so that ingestion health is visible and actionable.

**Notifications and reminders from the app.** Ensure in-app notifications (and optional push) are reliable and that reminder delivery (email, WhatsApp, notification) is visible in the UI (e.g. "reminder sent" or "scheduled for X").

### d. Scale / Infra

**Unified health and self-test.** Provide one observability endpoint or page that checks EventStore, Postgres, Qdrant, Redis, Kafka (and optional Celery) and reports green/red per dependency. Run this in CI or on deploy to catch configuration errors early.

**Idempotency and at-least-once.** Document and optionally extend idempotency (e.g. longer TTL or persistent idempotency in Mongo) so that under Kafka or worker retries, duplicate processing is never visible to the user.

**Multi-tenant and cost.** Add tenant-level metrics (event volume, RAG queries, agent runs) and optional quotas or cost attribution so that multi-tenant usage is observable and controllable.

**Logging and tracing.** Standardize trace_id (and optionally span_id) across pipeline, RAG, and agents so that a single request or event can be followed through the system in logs.

### e. Integrations

**Calendar as time authority.** Integrate calendar more deeply: e.g. "free slots" or "next meeting" as input to planning agents, and optional "block time for this task" as an execution action so that the second brain and calendar stay aligned.

**Gmail send and labels.** Add send_email as a first-class action (already in execution) and optionally "mark as read" or "add label" so that the brain can act on email, not only ingest it.

**Slack threads and reactions.** Extend Slack integration to read threads and optionally post replies or reactions so that conversations are captured and the system can participate where appropriate.

**One additional source.** Add one new connector (e.g. a notes app, another calendar, or a CRM) using the same pattern (normalize to unified payload, external_id, optional cursor) to prove the model and increase coverage.

---

## 7. Strategic Recommendation

The single most important next step to move KIRP closer to an Ultimate Second Brain is to make the system **proactively useful every day** through a **daily brief** and **reliable scheduled reminders**.

Today, ingestion, schema, obligations, and reminders are implemented; the main gap is that the user must open the app or trigger sync and reminder runs manually (or depend on a correctly configured scheduler). Delivering one daily message that answers "what’s due, what’s on the calendar, and what matters" and ensuring reminders fire on time would create a habit loop: the user comes to expect the brief and the reminders, and the second brain becomes a daily presence rather than a tool they remember to check.

This step is the best leverage point because it uses existing building blocks: list_upcoming_obligations, calendar events (if connected), InsightsEngine (or a lightweight summary), and the execution layer (email or WhatsApp). It does not require new connectors or a new schema; it requires a single "briefing" flow (agent or service) that runs on a schedule, aggregates data, formats a message, and calls the same execution paths used for reminders. Implementing it would also force the team to fix and document the scheduler (Celery or equivalent) so that all scheduled agents, including reminders, run reliably.

Concrete user value: within a short time (e.g. one or two sprints), the user would receive a daily brief at a chosen time and would get reminders before deadlines via their chosen channels. That would make the second brain feel alive and useful every day and would set the stage for richer insights and deeper integrations later.

---

*Document generated from the KIRP codebase and configuration. No code snippets or TODOs; all claims are based on actual implementation or explicitly noted as uncertain.*
