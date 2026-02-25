# KIRP AI Layer — Improvement Plan

Focus: accuracy, efficiency (minimal tokens, minimal unnecessary LLM calls), human-like communication, adaptability, deep integration, proactive reasoning without waste, safety and determinism. Optimize for intelligence-per-token; do not inflate complexity or heavy LLM usage.

---

## 1. Current AI Capability Assessment

### Agents

**What works well.** The PHASE5 agents (PlannerAgent, InsightAgentV2, ReminderAgentV2, ExecutionAgent, OverloadAgent, ConflictAgent, SuggestFiltersAgent) are largely deterministic. PlannerAgent uses only SchemaEngine and GraphBuilder: it lists nodes, obligations, and tasks, sorts by due date, and builds daily/weekly plan and priorities without any LLM. InsightAgentV2 uses InsightsEngine and GraphBuilder only; InsightsEngine is fully heuristic (workload, overdue, today focus, commitments, patterns, recommendations). ReminderAgent and ReminderAgentV2 use list_upcoming_obligations and user preferences; delivery is via integrations. OverloadAgent, ConflictAgent, and SuggestFiltersAgent operate on schema nodes with simple counters and rules. FutureObligationsAgent is a thin wrapper over list_upcoming_obligations. These agents are efficient and predictable.

**What is inefficient.** PatternAnalyzerAgent fetches RAG context ("recent activity patterns") and then sends a long prompt to an LLM (bulk) to produce JSON patterns; the same patterns (habits, overload, procrastination, themes) can be derived from schema and event counts with heuristics. ForecasterAgent, TodayTomorrowPlannerAgent (in agents/planner.py), and RiskOpportunityAgent each call an LLM (critical) with large context to produce forecasts, plans, or risk lists; the core PlannerAgent (in core/agents) already produces daily/weekly plan and priorities without LLM. SchemaStructureAgent calls an LLM (bulk) to extract tasks/projects/life areas from text; the pipeline already uses life_objects.extract_life_objects (rule-based classification and date parsing) for the same purpose. PresentationAgent calls an LLM (ui) to generate Kanban/Timeline/Calendar views; views can be generated from schema nodes with fixed templates. MetaAgent always calls an LLM for routing even when the decision tree returns a single candidate; the LLM routing can be skipped when there is one high-scoring candidate. Legacy insight.py uses LLM (reasoning) for answers; InsightAgentV2 replaces this with InsightsEngine and does not use LLM.

**What is missing.** There is no central place that decides "when to call LLM" vs "when to use schema + rules." There is no embedding cache: every RAG search embeds the query, and every new event is embedded once in the pipeline (acceptable) but repeated similar queries (e.g. "what's due today") could reuse results. There is no feedback store for "user dismissed this insight" or "user acted on this suggestion" to adjust future behavior. Tone and response style are ad hoc; there is no Human Response Engine or style guide.

### RAG

**What works well.** RAG is tenant/space/user scoped. Hybrid search (semantic + BM25) is supported. Single-hop search embeds the query once and retrieves from Qdrant with filters. Embeddings are created once per event at ingest and stored in Qdrant; that is correct.

**What is inefficient.** Multi-hop retrieval calls an LLM for query expansion at each hop (entities + sub_queries), then runs additional searches. For many user queries (e.g. "what's due today"), multi-hop does not add value and multiplies cost (one LLM call per hop plus multiple embed + search). There is no cache for (query_embedding, tenant_id, space_id) → search results, so the same or similar question asked twice causes repeated embed + search. RAG is not used by the main "plan" or "insights" paths that the UI uses (InsightAgentV2 uses InsightsEngine, not RAG); RAG is used by PatternAnalyzer, legacy insight, and potentially /ask. So RAG usage is already limited but where it is used, multi-hop and missing cache add cost.

**What is missing.** Embedding cache for frequent query patterns (e.g. "upcoming obligations", "recent activity"). A rule: "if query is asking for obligations or plan, use SchemaEngine only and do not call RAG." Optional: cache search results keyed by (query_hash, tenant, space) with short TTL to avoid duplicate work in the same session.

### SchemaEngine

**What works well.** SchemaEngine is the source of truth for tasks, projects, commitments, life areas. list_upcoming_obligations, list_nodes, get_node, upsert_node are used consistently by the pipeline and agents. Life-object extraction in the pipeline is rule-based (classify_content, parse_due_date) and does not call LLM. This is efficient and deterministic.

**What is inefficient.** Nothing material; schema layer is already lean.

**What is missing.** Schema-only APIs could be exposed for "plan" and "obligations" so the UI or a briefing flow never triggers RAG or LLM for those queries.

### EventPipeline

**What works well.** Pipeline runs governance → store → embed (one call per event) → Qdrant upsert → history → extract_life_objects → upsert_node. Life-object extraction is heuristic. Embedding is necessary once per event for semantic search later; that is acceptable.

**What is inefficient.** If DISABLE_EMBEDDINGS is false, every event is embedded; for high-volume ingest (e.g. bulk sync), that can be many embedding calls. Option: batch embedding or defer embedding for non-interactive sync (e.g. run embeddings in a background pass with a cap per run).

**What is missing.** No distinction between "user-facing event" (embed immediately) and "bulk sync event" (embed in batch or on-demand when first queried).

### Execution engine

**What works well.** Execution is deterministic: command type → integration call → audit. No LLM involved.

**What is missing.** Nothing from an AI-efficiency perspective.

### InsightsEngine

**What works well.** Fully deterministic. Uses schema nodes, obligations, and recent events; produces workload, overdue, today focus, commitments, patterns, connections, project progress, and recommendations with fixed templates and thresholds. No LLM. This is the right model for "insights" in production.

**What is missing.** Optional: allow tuning thresholds (e.g. "overdue" grace minutes, "many tasks" count) per user or tenant via stored preferences, still without LLM.

### UI interactions

**What works well.** Dashboard and second-brain call getStats, listEvents, listAgents, getInsightsV1; tasks/nodes come from SchemaEngine. Running an agent is explicit (user clicks run); not every page load triggers an LLM.

**What is inefficient.** If the user opens "insights" and the backend runs InsightAgentV2, that is cheap (no LLM). If the user runs "Pattern Analyzer" or "Forecaster" or "Plan" (and the system routes to the legacy TodayTomorrowPlannerAgent or an LLM-based agent), that triggers RAG + LLM or LLM. So the inefficiency is in which agent is bound to which UI action and in MetaAgent always calling LLM for routing.

**What is missing.** UI could offer "Quick plan" (PlannerAgent only, no LLM) vs "Deep plan" (optional LLM) so that default path is zero-LLM. Same for insights: default to InsightAgentV2 only.

### Reminder / obligation logic

**What works well.** Obligations are list_upcoming_obligations (schema). Reminder logic uses ReminderPreferencesStore (lead_hours, channels) and ReminderSentStore (dedup). No LLM. Deterministic and correct.

**What is missing.** Nothing for efficiency; optional self-improvement could adjust lead_hours or channel preference from user behavior (see Section 5).

---

**Summary of findings**

| Area            | Works well                          | Inefficient / overuses LLM                    | Can be replaced with deterministic logic   |
|-----------------|-------------------------------------|-----------------------------------------------|---------------------------------------------|
| Agents          | PlannerAgent, InsightAgentV2, Reminder*, Overload, Conflict, SuggestFilters, Execution, FutureObligations | PatternAnalyzer, Forecaster, TodayTomorrowPlanner (agents/), RiskOpportunity, SchemaStructure, Presentation, MetaAgent (always LLM route) | Pattern analysis, forecast, plan narrative, risk list, schema extraction, view gen, routing when 1 candidate |
| RAG             | Scoping, single-hop, one embed per event at ingest | Multi-hop (LLM per hop + multiple searches), no query/result cache | Multi-hop for most queries; use schema for "plan" and "obligations" |
| SchemaEngine    | All current usage                   | —                                             | —                                           |
| EventPipeline   | Life-object extraction heuristics   | One embed per event (could batch for bulk)    | —                                           |
| InsightsEngine  | All heuristic insights              | —                                             | —                                           |
| Reminder/Obligation | Deterministic, preferences, dedup | —                                             | —                                           |

---

## 2. Efficiency Plan (Token Optimization)

### When to call LLMs

- **User explicitly asks an open-ended question** (e.g. /ask or command with natural language that cannot be mapped to "obligations," "plan," "insights" by keywords). One LLM call for answer or routing, then one agent run.
- **Optional "deep" analysis** when the user explicitly requests it (e.g. "analyze my patterns in depth" or "explain why this recommendation") and only after a deterministic summary is shown.
- **Query expansion in RAG** only when single-hop search returns too few results (e.g. below a threshold) and the query is complex; not for every search.

### When NOT to call LLMs

- **Obligations, plan, priorities:** Use SchemaEngine.list_upcoming_obligations and PlannerAgent (core) only. No RAG, no LLM.
- **Insights:** Use InsightsEngine and InsightAgentV2 only. No LLM.
- **Reminders:** Already no LLM. Keep as is.
- **MetaAgent routing:** When the decision tree returns exactly one candidate with high score, route to that agent and skip LLM. Call LLM only when there are multiple candidates or none.
- **Pattern analysis:** Replace LLM with heuristic rules over schema + event counts (e.g. "recurring source" = habit, "overdue count > threshold" = procrastination, "active tasks > 30" = overload). Same for Forecaster and RiskOpportunity: use schema-based forecasts (e.g. "tomorrow’s load = tasks due tomorrow") and risk list (overdue + due-soon commitments).
- **Schema extraction from text:** Pipeline already uses life_objects; do not call SchemaStructureAgent with LLM for ingest. If SchemaStructureAgent is ever used for "parse this blob," prefer a small set of rules or a single small LLM call with a strict output schema and low max_tokens.
- **Presentation (Kanban/Timeline/Calendar):** Generate from schema nodes with fixed templates (group by status, by due_date, by life_area). No LLM.
- **Multi-hop RAG:** Default to single-hop. Enable multi-hop only when single-hop returns fewer than N results and query length > M characters, and cap to one expansion (one LLM call max).

### How to reuse embeddings

- **Query embedding cache:** In RAG, before calling embed(query), hash (query.strip().lower(), tenant_id, space_id). If a result exists in cache (e.g. Redis or in-memory with TTL 5–10 minutes) for this key, return cached results instead of embedding and searching. Invalidate on new ingest for that tenant/space if needed.
- **Event embeddings:** Keep one embedding per event at ingest. For bulk sync, consider a queue: write event to store first, embed in a separate worker with a rate limit so that token usage is smooth and bounded.
- **Reuse RAG results for similar queries:** If the UI sends "upcoming obligations" and "what do I need to do," map both to the same internal query ("obligations") and serve from SchemaEngine, not RAG; no embedding needed.

### How to use schema + rules instead of LLMs

- **Patterns:** From schema: count tasks by source (gmail, calendar, notion), by status (pending vs completed), by due_date (overdue, today, this week). Habits = "same source recurring"; overload = "active count > 30"; procrastination = "overdue > 5"; themes = top N words from task titles (e.g. simple word bag). Output the same JSON shape as today so the UI does not change.
- **Forecast:** "Tomorrow’s load" = count of tasks with due_date in tomorrow; "bottlenecks" = projects with many pending children and near due date. No LLM.
- **Risk/opportunity:** Risks = overdue commitments + commitments due in 24h; opportunities = "completed this week" + "free slots" (if calendar is integrated). Return list of items with type and reason string from templates.
- **Plan narrative:** PlannerAgent already returns daily_plan, weekly_plan, priorities. Add one deterministic "summary" string: e.g. "You have {n} overdue, {m} due today, {k} this week." No LLM.
- **View generation:** PresentationAgent: input = list of nodes + view_type (kanban|timeline|calendar). Group nodes by status (kanban), by due_date (timeline), by date (calendar). Output fixed JSON. No LLM.

### How to precompute insights

- **Scheduled job:** Run InsightsEngine.compute_insights(tenant_id, space_id, user_id) on a schedule (e.g. every 6–12 hours per user or on first request of the day). Store results in a cache (e.g. MongoDB collection or Redis) keyed by (tenant_id, space_id, user_id, date). When the UI requests insights, return cached if fresh (< 6h); otherwise compute and cache. Reduces repeated schema + event reads and keeps response fast.
- **Daily brief:** Precompute once per day (obligations, today tasks, one summary sentence from InsightsEngine). Store per user. No LLM in the brief; only templates.

### How to avoid repeated queries

- **Session or short-lived cache:** For the same user session, cache "obligations" and "plan" for 1–5 minutes so that multiple tabs or quick refreshes do not hit the backend repeatedly.
- **Backend:** list_upcoming_obligations and list_nodes already support use_cache in SchemaEngine; ensure cache is used for read-heavy endpoints and invalidated on write.

### How to use short prompts with high signal

- When an LLM call is truly needed (e.g. open-ended ask), use a short system prompt: "You are KIRP. Answer in 1–3 short sentences. Be direct." User message only; do not inject full RAG context into the prompt. Retrieve top-k chunks, put them in a short "Context:" block (e.g. 500 chars), then ask: "Using only the context above, answer: {query}". Max_tokens 150–300.
- For routing (when used), prompt: "Query: {query}. Candidates: A, B, C. Reply with one letter." No agent descriptions in the prompt if the decision tree already narrowed to 2–3 agents; optionally include one line per candidate.

---

**Agents and optimization**

| Agent                     | Current LLM use     | Optimization |
|---------------------------|---------------------|--------------|
| PatternAnalyzerAgent      | Yes (bulk)          | Replace with schema/event heuristics; same output shape. |
| ForecasterAgent           | Yes (critical)      | Replace with schema-based counts and templates. |
| TodayTomorrowPlannerAgent | Yes (critical)      | Deprecate or route to PlannerAgent (core) only. |
| RiskOpportunityAgent      | Yes (critical)      | Replace with overdue + due-soon + completed heuristics. |
| SchemaStructureAgent      | Yes (bulk)          | Do not use for ingest; pipeline uses life_objects. For ad-hoc parsing, use rules or one small LLM call with strict schema. |
| PresentationAgent        | Yes (ui)            | Replace with template-based grouping from schema. |
| MetaAgent                 | Yes (routing)       | Skip LLM when decision tree returns one candidate; call LLM only for tie-break or multiple candidates. |
| insight.py (legacy)       | Yes (reasoning)     | Prefer InsightAgentV2; if keep, use short prompt + RAG top-3 only. |
| RAG multi-hop             | Yes (reasoning per hop) | Default single-hop; multi-hop only if results < N and one expansion max. |

**Flows that currently overuse LLMs**

- MetaAgent route: every /command/execute triggers one LLM call even when the decision tree has one clear candidate.
- PatternAnalyzer, Forecaster, RiskOpportunity: one LLM call per run with large context.
- RAG multi-hop: one LLM per hop plus multiple embed+search.
- SchemaStructureAgent and PresentationAgent when invoked: one LLM each.

**Flows that can be replaced with deterministic logic**

- All of the above agent LLM uses (patterns, forecast, risk, plan narrative, schema extraction, view gen).
- MetaAgent routing when candidates count is 1.
- "What’s due today" / "plan" / "obligations" → SchemaEngine + PlannerAgent only.

---

## 3. Human-like Response Layer

### How the system should respond

- **Naturally:** Short sentences. Avoid "Based on my analysis," "I have detected," "It appears that." Prefer "You have 3 overdue tasks" / "Tomorrow: 5 items."
- **Maintain context:** Within a session, refer to "today’s plan" or "those 3 tasks" if the user already asked for the plan. Do not repeat the full list every time; offer "Want details on any of them?"
- **Avoid robotic phrasing:** No bullet-heavy walls. Use one line for the main point, then optional detail. Vary phrasing (e.g. "3 things due today" vs "You have 3 due today").
- **Short and clear:** Default to 1–3 sentences for summaries; expand only when the user asks ("why?" / "tell me more").
- **Adapt tone:** If the user writes in short, casual style, keep replies short. If they ask formally, keep replies clear but still concise. No need for LLM to adapt; use 2–3 preset "tones" (neutral, casual, minimal) chosen by user preference or inferred from recent message length.
- **Explanations only when needed:** Do not explain how the system works unless the user asks. For recommendations, one line of reason is enough ("Because it’s overdue" / "Due tomorrow").

### Human Response Engine — design

**Rules**

- Max 2–3 sentences for any automatic summary (brief, insight summary, plan summary).
- No opening filler ("Sure!" / "Of course!" / "I’d be happy to."). Start with the content.
- Numbers and dates in a consistent format (e.g. "3 tasks" / "Feb 15").
- For lists: "A, B, and C" or "A; B; C" — no "1. 2. 3." unless the user asked for a list.
- If the system cannot answer (e.g. no data): say "No tasks due today" or "Connect a source to see events," not "I’m sorry, I couldn’t find…"

**Style guide**

- Prefer active voice: "You have 3 overdue" not "There are 3 overdue tasks."
- Prefer "you" and "your": "Your plan for today" not "The plan for today."
- Avoid hedging: "You have 3 overdue" not "You might have around 3 overdue."
- For recommendations: "Do X" or "Consider X" — one verb, then reason in few words if needed.

**Tone adaptation logic**

- Store a simple preference: response_style = neutral | casual | minimal (default: neutral).
- neutral: Full sentences, polite. "You have 3 tasks due today. I recommend starting with X."
- casual: Shorter, contractions. "3 due today — start with X?"
- minimal: Almost telegram-style. "3 today. Start: X."
- No LLM for tone; use templates per tone. Optionally infer style from the last N user messages (avg length, punctuation) and set default per user.

**When to use LLM vs templates**

- **Templates:** All summaries (plan, obligations, insights, brief), reminders, error messages, empty states, confirmation messages. Templates are filled with numbers and entity names from schema/RAG.
- **LLM:** Only when the user asks an open-ended question that is not "plan," "obligations," "insights," "what’s due," etc. Then one short prompt with minimal context and low max_tokens. Optionally post-process LLM output with a single pass: trim to 2–3 sentences, remove filler.

**Implementation**

- Add a small module (e.g. human_response_engine.py): functions like format_plan_summary(plan_dict, tone), format_insight_summary(insight, tone), format_brief(obligations, today_count, tone). All take structured data and return a single string. No LLM inside.
- Where the API or agent returns "insights" or "plan," run the response through these formatters before sending to the UI so that the UI always gets human-like text.

---

## 4. Proactive Intelligence (Without Waste)

### Goals

- Predict obligations (already done: list_upcoming_obligations).
- Suggest actions (e.g. "start with X" from priorities; use deterministic rules: e.g. oldest overdue, or first due today).
- Detect patterns (heuristic: recurring sources, overdue rate, completion rate).
- Daily/weekly brief: one message per day (or week) with obligations, today’s tasks, one insight line.
- Surface insights at the right time: e.g. when the user opens the app (show cached insight) or at a fixed time (push brief).

### Without heavy agents or constant LLM

- **Cached embeddings:** Do not re-embed for proactive flows. Proactive flows do not use RAG; they use SchemaEngine and cached insights.
- **SchemaEngine queries only:** Daily brief = list_upcoming_obligations(due_from=today_start, due_to=today_end) + list_nodes (tasks due today) + one precomputed insight from InsightsEngine (cached). No RAG, no LLM.
- **Lightweight heuristics:** "Suggest action" = pick first task from "overdue" or "due today" sorted by due_date; or pick the task with highest priority if set. "Pattern" = e.g. "You completed 5 tasks this week" from schema counts.
- **Event triggers instead of polling:** When a new event is ingested (webhook or sync), optionally enqueue a lightweight job "invalidate insight cache for this user" or "recompute brief for this user if next send is within 1h." Do not run full agent suite on every event; run only reminder check (obligations + preferences + sent store) and optionally one InsightsEngine compute and cache update. Scheduled brief: one cron per user per day that reads cache or runs InsightsEngine once and sends the brief via execution layer.

### Concrete design

- **Brief job (daily):** For each user with reminder_preferences or last_active: load obligations (today + next 7d), today tasks, cached insight summary (or run InsightsEngine once). Format with Human Response Engine. Send via email or WhatsApp using execution layer. No LLM, no RAG.
- **On ingest:** After pipeline.run(), optionally push "insight_cache_stale" for (tenant_id, user_id). A worker or next request can recompute insight cache once per 6h per user.
- **Reminders:** Already event-driven (scheduled run); no change. Keep ReminderAgent logic as is.
- **Suggestions on dashboard:** "Suggested focus" = first overdue or first due today from PlannerAgent output. No LLM.

---

## 5. Self-Improvement Loop

### Goals

- Learn from user actions (e.g. completed a task, dismissed a suggestion, clicked a recommendation).
- Learn from dismissed vs accepted suggestions to adjust what we show.
- Adjust priorities (e.g. prefer "due today" over "overdue" if the user often completes today first).
- Improve prompts (optional, minimal): if we keep one LLM path, store last N (query, response, feedback) and periodically tune a one-line instruction.
- Improve agent behavior: e.g. ReminderAgent lead_hours per user from "user often snoozes" or "user completes right after reminder."

### Constraints

- Lightweight: no heavy ML. Use counters, thresholds, and simple rules.
- Token-efficient: no LLM in the loop for learning; only for optional prompt tweak (rare).
- Deterministic: same inputs → same outputs; learning only changes stored parameters (numbers, flags).
- Safe: no automatic change of permissions or data; only preference and ranking.

### Design

**Feedback store (MongoDB or Postgres)**

- Schema: (tenant_id, user_id, entity_type, entity_id, action, optional_meta, created_at). Actions: dismissed_insight, accepted_insight, completed_task, clicked_recommendation, snoozed_reminder, changed_reminder_preference.
- Write only; no LLM. On "dismiss insight" or "mark recommendation done," insert one row.

**Aggregates (computed periodically or on read)**

- Per user: count dismissed_insight by insight type (e.g. "overdue", "recommendation"); count accepted_insight by type. Ratio accepted/(accepted+dismissed) per type.
- Per user: avg time from reminder to task completion (if we log reminder_sent and task completed_at). Prefer lead_hours that correlates with completion.
- Store in a small collection or JSON: user_preferences_derived: { user_id, tenant_id, insight_weights: { type: weight }, preferred_lead_hours?: number, ... }. Updated every 24h or on next login.

**Use of aggregates**

- **Insights ranking:** When returning insights, sort by confidence * (1 + insight_weights[type]). So types the user often accepts rank higher; types they dismiss rank lower. Deterministic.
- **Reminder lead time:** If we have data, suggest "Your reminders might work better with lead_hours = X" in settings (optional); user confirms. Do not auto-change without consent.
- **Suggestions:** "Suggested focus" can prefer task types or life areas the user interacts with more (e.g. if they often complete "work" tasks first, put work first in the list). Use simple counts from feedback store.

**Prompts (optional)**

- If one LLM path remains (e.g. open-ended ask), store last 10 (query, response, thumbs up/down). Once a week or on demand, compute "response was good when we included X." Update one line in the system prompt (e.g. "Prefer answers that mention specific tasks when relevant."). Manual review before deploy. No automatic prompt injection from user content (safety).

**No automatic agent behavior change**

- We do not change agent code or routing from feedback. We only change ranking, weights, and optional suggested settings. So behavior stays predictable and safe.

---

## 6. Implementation Roadmap

### Step 1: Replace LLM in MetaAgent when one candidate (fast win)

- **Change:** In MetaAgent.route(), if decision_tree_candidates has exactly one agent and that agent’s score >= 0.5, call that agent and return; skip LLM routing.
- **Impact:** Saves one LLM call per /command/execute when the query clearly maps to one agent (e.g. "what’s my plan" → PlannerAgent).
- **Cost:** Zero tokens in that path.
- **Dependencies:** None.
- **Measure:** Count of MetaAgent runs that take "decision_tree_only" path vs "llm_routing" path; track token usage before/after.

### Step 2: Route "plan" and "obligations" to schema-only agents (no RAG, no LLM)

- **Change:** In command/execute or MetaAgent, if query matches keywords ("plan", "today", "tomorrow", "obligations", "what’s due", "what do I need to do"), route directly to PlannerAgent or FutureObligationsAgent. Do not call RAG; do not call any LLM-based planner.
- **Impact:** All plan/obligation requests become zero-LLM, zero-RAG.
- **Cost:** Zero tokens.
- **Dependencies:** Step 1 (so that routing is deterministic for these keywords).
- **Measure:** Ratio of plan/obligation requests that hit PlannerAgent vs legacy TodayTomorrowPlannerAgent; ensure no regression in response quality (user-facing plan still has daily_plan, weekly_plan, priorities).

### Step 3: Add Human Response Engine (templates)

- **Change:** Add human_response_engine.py with format_plan_summary, format_insight_summary, format_brief, format_empty. Integrate into API responses that return plan or insights (e.g. PlannerAgent result, InsightAgentV2 result, future brief endpoint). Add response_style to user or tenant (default neutral).
- **Impact:** All summary text becomes short, human-like, consistent.
- **Cost:** No tokens.
- **Dependencies:** None.
- **Measure:** Subjective review of 20 sample responses; average length (chars) of summary strings.

### Step 4: Replace PatternAnalyzer LLM with heuristics

- **Change:** Implement pattern heuristics: habits = group events/tasks by source, count; overload = active_tasks > 30; procrastination = overdue > 5; themes = top 5 words from task titles (stopwords removed). Output same JSON shape (patterns[], summary). Wire PatternAnalyzerAgent handler to this.
- **Impact:** One LLM call removed per pattern run.
- **Cost:** Zero tokens for this agent.
- **Dependencies:** None.
- **Measure:** Compare output shape and count of patterns vs old LLM output; ensure UI still works.

### Step 5: Replace Forecaster and RiskOpportunity with heuristics

- **Change:** ForecasterAgent: tomorrow_load = count(tasks due tomorrow); bottlenecks = projects with >50% pending children and due in 7d. RiskOpportunityAgent: risks = overdue commitments + due in 24h; opportunities = completed_this_week + optional free_slots. Return list with type and template reason. Same output shape as before where possible.
- **Impact:** Two agents become zero-LLM.
- **Cost:** Zero tokens.
- **Dependencies:** None.
- **Measure:** Same as Step 4.

### Step 6: RAG single-hop default; multi-hop only when needed

- **Change:** In RAG search(), if enable_multihop is true, first run single_hop_search. If len(results) >= threshold (e.g. 5), return immediately. Else run at most one expansion (one LLM call), then one more search; merge and return. Remove iterative loop of multiple hops.
- **Impact:** Most queries use zero LLM in RAG; complex queries use one LLM call max.
- **Cost:** Large reduction in RAG LLM and embed calls for multi-hop.
- **Dependencies:** None.
- **Measure:** RAG multi-hop call count and token usage before/after.

### Step 7: Query/result cache for RAG

- **Change:** Before embed(query) in RAG, check cache (e.g. Redis key = hash(query, tenant_id, space_id)); TTL 5–10 min. On hit, return cached results. On miss, run search and store result in cache.
- **Impact:** Repeated identical queries in a session cost zero.
- **Cost:** Minimal (Redis memory).
- **Dependencies:** Redis (already used for idempotency).
- **Measure:** Cache hit rate; reduction in embed + search calls.

### Step 8: PresentationAgent templates

- **Change:** PresentationAgent: accept view_type and list of nodes; group by status (kanban), due_date (timeline), or date (calendar). Return JSON. Remove LLM call.
- **Impact:** One LLM call removed per presentation request.
- **Cost:** Zero tokens.
- **Dependencies:** None.
- **Measure:** UI still renders Kanban/Timeline/Calendar from new output.

### Step 9: Precomputed insight cache

- **Change:** Add insight_cache collection or Redis key per (tenant_id, space_id, user_id). On first request of the day or every 6h, run InsightsEngine.compute_insights and store. API returns cache if fresh; else compute and update cache.
- **Impact:** Repeated insight requests are cheap; first request or after 6h pays once.
- **Cost:** No extra tokens; slightly more storage and one batch read per user per 6h.
- **Dependencies:** None.
- **Measure:** P95 latency for GET insights; cache hit rate.

### Step 10: Daily brief (no LLM)

- **Change:** Add brief job: for each user (with preferences or active in last 7d), load obligations (today + 7d), today tasks, one cached insight line. Format with Human Response Engine. Call execution layer (email or WhatsApp). Run once per day per user (cron or scheduler).
- **Impact:** Proactive value without any LLM.
- **Cost:** Zero tokens; one execution send per user per day.
- **Dependencies:** Step 3 (format_brief), execution layer, reminder_preferences or similar to know where to send.
- **Measure:** Delivery success rate; user opt-out rate if we add preference.

### Step 11: Feedback store and ranking

- **Change:** Add feedback collection and write on dismiss_insight, accepted_insight, completed_task (if not already). Add periodic aggregate (e.g. daily): insight_weights per type per user. When returning insights, multiply confidence by (1 + weight) and re-sort. Store in user_preferences_derived.
- **Impact:** Insights order improves over time without LLM.
- **Cost:** No tokens; small read/write.
- **Dependencies:** UI to send dismiss/accept (if not already).
- **Measure:** Dismiss rate per insight type over time; acceptance rate.

### Step 12: Deprecate or gate legacy LLM agents

- **Change:** Remove or hide from UI: TodayTomorrowPlannerAgent (agents/planner.py), legacy insight.py handler if still registered. Ensure "plan" always routes to PlannerAgent (core). Optionally keep SchemaStructureAgent for ad-hoc use only (e.g. admin) with one small LLM call and strict schema; do not use in pipeline.
- **Impact:** No accidental use of heavy planners or legacy insight.
- **Cost:** Zero tokens from those agents.
- **Dependencies:** Step 2.
- **Measure:** No traffic to deprecated agents.

---

## 7. Additional Improvements (Inferred)

### Missing components

- **Central "should I use LLM?" gate:** A single function or policy that all entry points (command/execute, agent run, RAG search) call: e.g. use_llm(query, context) -> bool. Returns false for "plan," "obligations," "insights," "what’s due," and for RAG when single-hop is sufficient. Reduces duplication of "if keyword then schema-only" across the codebase.
- **Embedding budget per tenant/user:** Optional cap: max N embeddings per day per tenant (or per user) for RAG queries; after that, only cached or schema-only. Prevents runaway cost from a single tenant.
- **Structured logging for AI cost:** Log every LLM call and every embed call with tenant_id, user_id, agent_or_path, token_estimate. Enables cost attribution and finding remaining heavy paths.

### Missing heuristics

- **"Suggested focus" on dashboard:** Deterministic: first overdue task, or first due-today task, or "No urgent tasks." No LLM. Can use PlannerAgent output; just take the first item from daily_plan or overdue.
- **"You might have forgotten" for commitments:** If a commitment has due_date in the past and status != completed, add to a simple "might have forgotten" list. One line in brief or insights. No LLM.
- **Life-area balance:** From schema, count tasks per life area. If one area has >60% of tasks, add insight "Most tasks are in {area}." Suggests diversification. Already possible from existing data; just add one heuristic in InsightsEngine.

### Missing UX flows

- **"Quick plan" vs "Deep plan":** In UI, "Quick plan" = PlannerAgent only (zero LLM). "Deep plan" = optional future: add one short LLM summary line. Default to Quick plan so that the main path is fast and free.
- **Insight "Why this?":** When user clicks "Why?" on an insight, show the underlying data (e.g. "Based on 3 overdue tasks and 5 due today") from the insight’s data payload. No LLM; just format the existing fields.
- **Reminder preview:** In reminder preferences, "Preview" could show "You’d get a reminder for: [list of next 3 obligations with due date]." Uses list_upcoming_obligations + lead_hours; no LLM.

### Missing caching layers

- **SchemaEngine list_nodes cache:** Already has use_cache; ensure it is used in all read-heavy list paths and invalidated on upsert_node/update_node/delete. Review TTL and key (tenant_id, space_id, entity?).
- **Obligations cache:** list_upcoming_obligations could be cached for 1–5 minutes per (tenant_id, space_id, user_id, due_from, due_to) to avoid repeated DB hits when the dashboard and brief both call it.

### Optional lightweight agents

- **BriefComposerAgent:** No LLM. Input: obligations, today_count, one_insight_line. Output: one short paragraph from Human Response Engine. Used only by the daily brief job. Ensures one place for brief formatting.
- **FocusSuggestorAgent:** No LLM. Input: daily_plan, overdue. Output: single task id or title "Suggested focus: X" using rule (first overdue, else first due today). Used by dashboard "suggested focus" slot.

---

## Summary

The plan keeps the existing architecture and strengthens it: SchemaEngine, EventPipeline, InsightsEngine, and the deterministic agents remain the backbone. LLM use is restricted to open-ended user questions and optional deep analysis; all plan, obligations, insights, reminders, patterns, forecast, risk, and presentation are moved to schema + rules + templates. A Human Response Engine ensures short, human-like text. Proactive value comes from a daily brief and cached insights, without constant agents or LLM. A small feedback loop improves ranking and preferences over time in a deterministic, safe way. The implementation roadmap is ordered for quick wins (routing, plan/obligations, response engine) and then systematic replacement of each LLM-heavy agent and RAG multi-hop, followed by cache, brief, and feedback.

[CURSOR AI UPGRADE PLAN] Completed.
