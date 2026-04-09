## System Overview
Version: v0.x (production-hardening)
Last Updated: 2026-04-11
Mode: controlled hardening (no capability removal)

### Milestone: 100% EventPipeline.run lifecycle coverage — **achieved**
- Every **`EventPipeline.run`** path either receives **`metadata.run_id`** + **RunController** state (Kafka ingest, M3 HTTP, registry **`handle_ingest_v1`** / **`handle_m3_event`**) or **creates** a run at the worker boundary (**`connector_sync`**, **`notion_sync`**, **`ingest_task`**) before calling **`run`**.
- **`PIPELINE_RUN_POLICY`**: default **`warn`** (visibility: **`PIPELINE_NO_RUN_ID`** / **`PIPELINE_ORPHAN_RUN_ID`** + counters **`kirp_pipeline_no_run_id_total`**, **`kirp_pipeline_orphan_run_id_total`**); **`strict`** → **`RunStateMissing`** (`PIPELINE_RUN_ID_REQUIRED` / `PIPELINE_RUN_STATE_MISSING`). Legacy orphan fail-fast: **`STRICT_RUN_BOUNDARY_FAIL_FAST`** in **`warn`** mode only.
- **Tests:** `tests/test_pipeline_run_lifecycle.py` (strict + metrics + legacy fail-fast).
- **Grafana:** import **`deploy/grafana/kirp_pipeline_dashboard.json`** (pipeline counters by `event_type` / `source`).

## RunController & Redis — single source of truth (keys & behavior)

**This section is authoritative** for how run lifecycle state is stored and read *today*. Code: **`src/core/run_controller.py`**.

### Canonical Redis keys (current)

| Key | Type | Role |
|-----|------|------|
| **`tenant:{tenant_id}:{run_id}`** | Hash | **Canonical** run document: `state`, `steps` (JSON), `tenant_id`, `run_id`, `trace_id`, `workflow_type`, `idempotency_key`, `cost`, timestamps, etc. TTL ~7d from last write. |
| **`run_lookup:{run_id}`** | String | Value = **`tenant_id`**. Same TTL as the run hash. Resolves partition when code calls **`get_run_state(run_id)`** without an explicit tenant. |

**`run:{run_id}` is not canonical** — it exists only as an **optional legacy** read/write target (see env flags below).

### Writes (`set_run_state`)

- Always updates the in-process **`run_states[run_id]`** map.
- When **`tenant_id`** on the state is non-empty and not `*`: delete + **`HSET`** + **`EXPIRE`** on **`tenant:{tenant_id}:{run_id}`**, then **`SET run_lookup:{run_id}`** with the same TTL.
- **Optional:** if **`RUN_CONTROLLER_WRITE_LEGACY_RUN_KEY=1`** (default **off**), also write the same hash mapping to **`run:{run_id}`**.

### Reads (`get_run_state`)

Typical order:

1. **In-memory** hit for `run_id` (tenant mismatch with explicit `tenant_id` arg → treat as miss).
2. **Redis:** resolve **`effective_tenant`**: explicit `tenant_id` argument, else **`GET run_lookup:{run_id}`**, else **`update_key_prefix`** default tenant on the controller.
3. If **`effective_tenant`** known: read hash **`tenant:{effective_tenant}:{run_id}`** (supports legacy JSON **`GET`** on wrong-type keys as fallback inside the reader).
4. If **`RUN_CONTROLLER_READ_LEGACY_KEYS=1`** (default **on**): if still no state, try **`run:{run_id}`** hash (migration / old data).

**HTTP:** **`GET /api/v1/run/{run_id}/status`** passes the authenticated tenant as **`tenant_id`** hint when auth is required.

### Listing and partial-run discovery

- **`get_recent_runs(tenant_id)`**: **`SCAN`** `tenant:{tenant_id}:*`; if **`RUN_CONTROLLER_SCAN_LEGACY_FOR_LIST=1`** (default **off**), also scan **`run:*`** and merge.
- **`list_run_ids_by_state`**: scans **`tenant:*`** (and optionally **`run:*`** when that flag is on).

### Env flags (RunController ↔ Redis)

| Variable | Default | Meaning |
|----------|---------|---------|
| **`RUN_CONTROLLER_READ_LEGACY_KEYS`** | **on** (`1`) | After partitioned read miss, try **`run:{run_id}`**. |
| **`RUN_CONTROLLER_WRITE_LEGACY_RUN_KEY`** | **off** (`0`) | If **on**, dual-write hash to **`run:{run_id}`**. |
| **`RUN_CONTROLLER_SCAN_LEGACY_FOR_LIST`** | **off** (`0`) | If **on**, include legacy **`run:*`** keys in list/partial scans. |

### `EventPipeline.run` vs `EventPipeline.run_post_ingest_for_event`

| Path | Run lifecycle enforcement? |
|------|----------------------------|
| **`EventPipeline.run`** | **Yes.** **`PIPELINE_RUN_POLICY`** (`warn` / `strict`), **`PIPELINE_NO_RUN_ID` / `PIPELINE_ORPHAN_RUN_ID`** logs, **`kirp_pipeline_*`** metrics, **`RunStateMissing`** in strict mode; **`RunController.update_step`** for pipeline phases when a run is bound. |
| **`EventPipeline.run_post_ingest_for_event(event_id)`** | **No.** **Outside** the same gate: loads an **existing** event by **`event_id`**, re-runs **embed → Qdrant → schema / life-objects** only. **No** `PIPELINE_RUN_POLICY` check, **no** requirement that **`run_id`** be present for the method entrypoint, **no** **`RunController`** step updates on this path (timelines in Run monitor are **not** extended here the way they are during a full **`run()`**). |

**Operational implication:** use **`run_post_ingest_for_event`** for **projection repair** (e.g. after **`update_by_external_id`**). Do **not** assume strict run-boundary or pipeline lifecycle metrics cover this path — observe via **event id**, **application logs**, and downstream stores (Qdrant/Postgres), not the primary **`run()`** step timeline.

### Regression tests

- **`tests/test_run_controller.py`** — canonical **`tenant:{tenant_id}:{run_id}`** + **`run_lookup`** writes (fake Redis); aggregate step / state behavior.
- **`tests/test_api_run_status.py`** — **`GET /api/v1/run/{run_id}/status`** JSON shape (RunController seeded in-process).

## Architecture Map (Code-Based)
1. Ingestion
   - API ingress in `src/main.py` (`/api/v1/ingest`) emits Kafka envelope via `src/agents/kafka_event_agent.py`.
   - Worker consumption in `src/workers/kafka_processor.py::process_event`.
2. Pipeline
   - Canonical dispatch via `src/core/event_registry.py` + handlers in `src/core/event_registry_handlers.py`.
   - Core flow in `src/core/pipeline.py::EventPipeline.run`:
     run lifecycle gate (warn/strict) → governance -> embed/upsert -> Mongo event write -> history write -> schema upsert.
3. Agents
   - Event agent run in `src/core/event_registry_handlers.py::handle_agent_run_v1`.
   - Runtime in `src/core/agent_engine.py::AgentExecutionEngine.execute_run`.
   - Scheduled runs in `src/core/agent_scheduler.py`.
   - M3 staged orchestration in `src/modules/m3/handlers.py` + `src/modules/m3/stages.py`.
4. Memory Layers
   - Mongo: events/history/agent logs/actions
   - Postgres: schema/life graph
   - Qdrant: semantic memory
   - Redis: idempotency/cache; **RunController** — see **RunController & Redis — single source of truth** (canonical **`tenant:{tenant_id}:{run_id}`** + **`run_lookup:{run_id}`**; legacy **`run:{run_id}`** optional). LLM quota / hourly alert counters: **`tenant:{tenant_id}:...`**
5. Workers / schedules
   - Kafka consumer `src/workers/kafka_processor.py`; Celery `src/workers/celery_app.py` + `src/workers/tasks.py`.
   - Reconciliation batch: `src/workers/reconciliation_worker.py` + `reconcile_partial_runs_task` (Celery beat every 15 minutes).
6. Output
   - API responses (`/ask`, `/m3/*`, `/agents/*`, `/api/v1/run/...`, `/api/v1/tenant/.../runs`, `/api/v1/tenant/.../runs/stream` SSE) from FastAPI routes in `src/main.py` and `src/api/*`.
   - Next.js dashboard (`app/(dashboard)/*`): **Run monitor** at `/monitoring` (`?tenant=` override) — stats pie, runs table, run detail modal (`/api/v1/run/{run_id}/status`), live refresh via **fetch + ReadableStream** on the SSE endpoint (15s) with Bearer token; dev default **port 3100** (`npm run dev`).

## Determinism / Consistency Findings
- Determinism breaks:
  - best-effort side writes in `EventPipeline.run` (Qdrant/history/schema failures are tolerated).
  - duplicated component assembly across `main.py`, `event_registry_handlers.py`, `modules/m3/handlers.py`, `kafka_processor.py`.
- Inconsistent state created when:
  - Mongo event persists but Qdrant/schema/history projections fail.
  - Redis idempotency is unavailable and duplicate events are reprocessed.
- **Detail:** see **Cross-store failure matrix** below (same file).

## Cross-store failure matrix (`EventPipeline.run` — current code behavior)

**Scope:** primary ingest path **`EventPipeline.run`** in `src/core/pipeline.py` (not **`run_post_ingest_for_event`** in isolation — that path is documented under *RunController & Redis*). **Canonical** for “what was accepted as the event” after a successful write is the **Mongo** document from **`EventStore.ingest`** (code comment: “source of truth”).

### Phase order vs stores (actual sequence)

| Order | Step | System | On success (RunController step, if run bound) | On failure |
|-------|------|--------|-----------------------------------------------|------------|
| 1 | Governance | OPA | `governance_check` → completed | **`PermissionError`** — pipeline stops; **no Mongo write** in this call. |
| 2 | Embed + vector upsert | **Qdrant** (RAG) | `qdrant_projection` → completed | **Caught:** WARNING log *“RAG embed/upsert failed (event still stored)”*; `qdrant_projection` → **failed**; pipeline **continues**. |
| 3 | Persist event | **Mongo** (`ingest`) | `mongo_write` → completed | **Uncaught:** exception propagates — **no** `history_write` / `schema_projection` in this invocation; **no** `mongo_write` completed step. **Note:** Qdrant may already have been updated in step 2 for the same planned `event_id`, while Mongo never persisted — **possible orphan vector** until retry or manual cleanup. |
| 4 | Timeline entry | **History** (Mongo-backed via `record_history`) | `history_write` → completed | **Caught:** WARNING *“History record failed after ingest”*; `history_write_failed` → **failed**; pipeline **continues** (Mongo event row from step 3 exists). |
| 5 | Life objects → graph | **Postgres** (SchemaEngine) | `schema_projection` → completed | **Caught:** WARNING *“Life-object extraction/upsert failed (event already stored)”*; `schema_projection` → **failed**; pipeline **continues**. |
| 6 | Terminal | — | `pipeline_start` + `pipeline_complete` → completed (if run bound) | N/A |

### What is “canonical” after a full or partial success

| Data | Canonical location | If downstream failed |
|------|-------------------|----------------------|
| Event body, `metadata`, `tenant_id`, `event_id` | **Mongo** event store (after successful **`ingest`**) | N/A for failures before ingest; after ingest, row exists even if Qdrant/history/Postgres failed. |
| Semantic search / RAG point | **Qdrant** | May be missing or stale if step 2 failed; **reconciliation** may replay via **`run_post_ingest_for_event`**. |
| Human “history” timeline row | **History** store (Mongo) | Missing if step 4 failed; **reconciliation** may **`replay_history_for_event`**. |
| Life graph nodes | **Postgres** (schema) | Missing/partial if step 5 failed; **reconciliation** may call **`run_post_ingest_for_event`** (schema path inside it). |

### Eventually reconciled vs stays inconsistent

| Situation | Reconciled? | Mechanism | Notes |
|-----------|-------------|-----------|--------|
| Aggregate run state **`partial`** (mix of completed + failed steps) and Mongo event exists for `metadata.run_id` | **Best-effort yes** | **`EventPipeline.reconcile_run`** + Celery **`reconcile_partial_runs_task`** | Only runs when **`list_run_ids_by_state("partial")`** picks up the run. |
| History step failed (`history_write_failed` / `history_write` failed) | **If** `reconcile_run` runs and replay succeeds | **`replay_history_for_event`** | Updates steps on success; may mark `history_write_failed` reconciled. |
| Qdrant and/or schema step failed | **If** `reconcile_run` runs and post-ingest returns **True** | **`run_post_ingest_for_event(event.id)`** then **`update_step`** `qdrant_projection` + `schema_projection` → completed | **`run_post_ingest_for_event` returns `True` whenever the event exists**, even if inner RAG or schema blocks only **log** warnings — **RunController timeline can show “completed” while logs still show projection warnings** (current code). |
| **Mongo `ingest` threw** (step 3) | **No automatic row** for that attempt | Retry / re-publish event | Run may never reach **`mongo_write` completed**; **reconcile_run** needs a Mongo event keyed by `run_id` — **cannot repair** if no stored event. |
| **Orphan Qdrant point** (step 2 ok, step 3 failed) | **Not** automatically deleted by this pipeline | Ops / manual / future tooling | Documented as **possible** inconsistency. |

### What operators see (RunController / logs / alerts)

| Signal | Source |
|--------|--------|
| **Run timeline** (`GET /api/v1/run/{run_id}/status`, Run monitor) | **`RunController`** Redis steps: `qdrant_projection`, `mongo_write`, `history_write` / `history_write_failed`, `schema_projection`, `pipeline_complete`, `reconciled`, etc. |
| **Aggregate `state`** | Derived from **latest status per step name** (e.g. `partial` when both failures and successes appear). |
| **Application logs** | WARNING lines for swallowed projection/history errors (see table above). |
| **Alerts** | **`RunController.update_step`** hooks **`on_run_controller_step`** — failed steps feed **hourly Redis counters** and optional **active alerts** / Slack (see *Production alerting* section). **Not every WARNING log** becomes an alert unless it maps to a **failed** run step recorded in Redis. |

### Regression tests

- **`tests/test_reconciliation_worker.py`** — **`EventPipeline.reconcile_run`** on aggregate **`partial`** (history replay / projection path vs **`run_post_ingest_for_event`** return semantics).

## Idempotency paths (current behavior)

**Two independent mechanisms** are in use; they do **not** share state. Code: **`kafka_processor.py`**, **`v1_m3.py`** (`/m3/reflect` only for HTTP idempotency).

### A — Kafka consumer (`process_event`) — Redis

| Aspect | Behavior |
|--------|----------|
| **Redis key** | **`idempotency:{derived_key}`** (string), TTL **`IDEMPOTENCY_TTL`** = **3600s** (1h) in `kafka_processor.py`. |
| **Derived key** (ingest path) | From `_get_event_idempotency_key`: explicit `idempotency_key` → `idem:{value}`; else `data.id` → `event:{id}`; else `run_id` → `run:{run_id}`; else `trace_id` → `trace:{trace_id}`; else SHA256 hash of full payload → `hash:…`. |
| **Agent run path** | Fixed key **`agent_run:{run_id}`** (string `run_id` from payload). |
| **When set** | After successful handling (`_mark_processed`), or early-return paths that skip duplicate work (e.g. already in Mongo by `event_id`). |
| **If Redis unavailable** | **`_check_idempotency`** logs a warning and returns **`False`** → **duplicate processing is allowed** for that message (no skip). **`_mark_processed`** may also fail silently (warning only). |

### B — M3 HTTP `POST /api/v1/m3/reflect` — M3 memory store

| Aspect | Behavior |
|--------|----------|
| **Trigger** | Optional header **`Idempotency-Key`** / **`idempotency-key`**. |
| **Scope** | **`tenant_id` + `user_id` + key`** via **`get_m3_memory_store()`** (`get_idempotency_event_id` / `record_idempotency`). |
| **On duplicate** | **HTTP 200** with same **`event_id`**; **no** second `registry.dispatch` / pipeline run for that key. |
| **Other M3 POSTs** | **`/m3/synthesis`** and **`/m3/evolution`** do **not** implement this header idempotency in code today — each call creates a **new** `run_id` and dispatches. |

### Operator expectations

| Question | Answer |
|----------|--------|
| Same ingest published twice to Kafka? | Skipped second time **only if** Redis idempotency sees the key within TTL **and** Redis is up. |
| Same reflection retried with same `Idempotency-Key`? | Short-circuited at **API** (M3 store), independent of Kafka Redis. |
| Strict pipeline / RunController? | **Orthogonal:** idempotency prevents **re-execution**; **`PIPELINE_RUN_POLICY=strict`** still requires **run state** for each execution that **does** run. |

### Regression tests

- **`tests/test_kafka_event_idempotency.py`** — **`_get_event_idempotency_key`** prefix priority (`idem:` / `event:` / `run:` / `trace:` / `hash:`) for the Kafka ingest path (section **A** above).

## Governance / OPA (`EventPipeline.run` — current behavior)

**Code:** `src/core/governance.py` — **`GovernanceEngine.check`**. The pipeline calls it with **`action="write"`**, **`resource="event"`** before Mongo ingest.

### When governance is “off”

| Condition | `GovernanceCheck` | Pipeline |
|-----------|-------------------|----------|
| **`opa_url` falsy** at engine construction (`bool(opa_url)` is **False**) | **`allowed=True`**, reason *Governance disabled (no OPA)*, **`requires_approval=False`** | Proceeds (no OPA HTTP call). Typical only if workers construct the engine with an empty URL. |

**Note:** Many call sites use **`os.getenv("OPA_URL", "http://opa:8181")`**, so **`_enabled` is usually True** in Docker-style deploys even if OPA is down.

### When OPA is enabled (`_enabled` True)

| Outcome | `allowed` | `requires_approval` | Pipeline (`EventPipeline.run`) |
|---------|-----------|---------------------|--------------------------------|
| HTTP **200** and policy result **allows** | **True** | May be **True** (M3 `identity_entropy_score` ≥ 0.6, or high risk score / policy flag) | **Proceeds**; M3 may trigger WhatsApp escalation when **`requires_approval`** (separate try/except, logged on failure). |
| HTTP **≠ 200** | **False** | **True** | **`PermissionError`** — **stops** before Mongo; RunController **`governance_check`** → **failed** if run bound. |
| **Network / timeout / parse exception** | **False** | **True** | Same: **`PermissionError`**; log **WARNING** *Governance check failed: …*. |

**Operational takeaway:** with a non-empty **`OPA_URL`**, **OPA unreachable behaves like a deny** (writes blocked), not fail-open. To run without OPA in dev, the engine must be built with a **falsy** URL (not merely a dead host).

### What operators see

| Signal | Where |
|--------|--------|
| Deny / OPA error | **`PermissionError`** from pipeline (caller-dependent: may surface as 500 or worker error); Run timeline **`governance_check`** **failed** when run exists. |
| Transient OPA failure | Same as deny until OPA recovers; **no** automatic retry inside **`check`** itself. |
| M3 escalation failure | **`logger.warning`** *M3 WhatsApp escalation failed* — ingest may still have completed if governance **allowed**. |

### Regression tests

- **`tests/test_governance_engine.py`** — **`GovernanceEngine(None)`** allows (no OPA); mocked OPA **HTTP ≠ 200** → **deny**; mocked transport error → **deny** + **`requires_approval`**.
- **`tests/test_core.py`** — **`GovernanceEngine(opa_url="")`** allows with disabled / OPA reason; **`Event`** **`to_doc` / `from_doc`** round-trip; **`AgentFramework`** register / **`list_by_trigger`**. Uses **`asyncio.run`** (no **`pytest-asyncio`** required).

## Metrics exposure (API — current behavior)

**Code:** `src/api/observability.py`; **registry:** `prometheus_client` **REGISTRY** (process-wide). **Collectors:** `MetricsCollector` in `src/observability/metrics.py`.

| Endpoint | Response | Use |
|----------|----------|-----|
| **`GET /observability/metrics/snapshot`** | **JSON** stub (`last_updated`, `namespaces` list) | Human / dashboard hints; **not** valid Prometheus scrape text. |
| **`GET /observability/metrics/prometheus`** | **OpenMetrics / Prometheus text** (`generate_latest(REGISTRY)`) | **Prometheus scrape target** for counters such as **`kirp_pipeline_*`**, **`kirp_kafka_*`**, etc. |
| Import **`prometheus_client` missing** | Prometheus route returns a **`#`-comment line** only | No series exported from that process. |

### Env / wiring

| Variable | Effect |
|----------|--------|
| **`DISABLE_PROMETHEUS=1`** | **`MetricsCollector.inc` / gauge / histogram are no-ops** — nothing registers in REGISTRY from those paths (by design for multiprocess safety). |
| **`deploy/prometheus.yml`** **`kirp-api`** job | Should use **`metrics_path: /observability/metrics/prometheus`** (see repo file). Scraping **`/metrics/snapshot`** will **not** ingest pipeline counters. |

**Dashboards:** Grafana JSON for **`kirp_pipeline_*`** lives under **`deploy/grafana/`** (see milestone bullet above).

### Regression tests

- **`tests/test_observability_metrics.py`** — **`GET /observability/metrics/prometheus`** and **`/metrics/snapshot`** return **200** with expected shape (smoke).

## Top 5 Production-Critical Weaknesses
1. ~~No unified run contract across API → Kafka → Pipeline → workers.~~ **Addressed for `EventPipeline.run`** (envelope + RunController + `PIPELINE_RUN_POLICY`); agent-only paths still rely on explicit `create_run` at API/Kafka boundaries.
2. Cross-store fanout consistency is best-effort (no first-class projection reconciliation ledger).
3. Pipeline/component initialization logic is duplicated in multiple runtime paths.
4. Idempotency behavior is split (Kafka Redis + M3 reflect only) — see **Idempotency paths (current behavior)**.
5. Model routing: **bulk defaults to Gemma4 (Ollama)** with optional budgets (`LLM_COST_BUDGET` / `LLM_LATENCY_BUDGET`); timeline step **`llm_call_*`** when invoke runs with `llm_run_context` set (ingest optional ack or any caller that sets context).

## Core Flows (Current State)
- Ingest: ✅ **run lifecycle** enforced at pipeline choke point; ⚠️ projection consistency still best-effort on partial failures
- M3: ✅ **HTTP routes** create run before dispatch; ⚠️ partial stage failures can still leave mixed state
- Ask: ✅ (RAG + LLM fallback path present)
- Agent Run: ✅ **RunController + LLM context** on registered paths; ⚠️ trace completeness depends on agent calling LLM / framework

## Infrastructure
- Kafka: ✅ (consumer retries + topic checks in worker)
- Redis: ⚠️ (RunController now retries + hash storage; idempotency/cache still degrade when Redis is down)
- Mongo: ✅ (canonical event store and operational stores)
- Postgres: ✅ (schema projection layer)
- Qdrant: ⚠️ (projection may fail while canonical write succeeds)
- OPA: ⚠️ (see **Governance / OPA** — non-200 or transport error **denies** writes when OPA URL is enabled)

## Current Focus (ONE Active Task)
👉 **Paused for Week 6 strategic direction** (M3 proactive agents / Kubernetes scale / SaaS billing).

## What Changed (Production alerting)
- **`src/core/alerting.py`**: on each `RunController.update_step`, **failed** steps increment hourly Redis counter; terminal **completed** steps (`pipeline_complete`, `agent_execute_complete`, `kafka_processed`) increment a success counter; thresholds → append **active alerts** JSON in Redis (`tenant:{tenant_id}:alerts:active`).
- **Env**: `ALERT_FAILURES_PER_HOUR` (default 5), `ALERT_FAILURE_RATE_THRESHOLD` (0.2), `ALERT_MIN_SAMPLES_FOR_RATE` (10), `ALERT_SLACK_WEBHOOK_URL` (optional), counter TTL `ALERT_COUNTER_TTL_SEC` / active TTL `ALERT_ACTIVE_TTL_SEC`.
- **API**: `GET /api/v1/tenant/{tenant_id}/alerts` — tenant-scoped list + count.
- **UI**: Run monitor page badge + SideNav dot on **Run monitor** when alerts exist.

## What Changed (LLM quotas / usage API)
- **`LLM_QUOTA_LIMIT_USD`**: when set &gt; 0, each `LLMClient.invoke` checks Redis counter `tenant:{tenant_id}:llm_cost` against a pre-call **ceiling** (`estimate_call_ceiling_usd`); on success increments by `track_cost` USD; over limit → **`QuotaExceeded`** → HTTP **429** (handler in `main.py`).
- **Tenant resolution**: `llm_tenant_id` contextvar (agents, ask) or `RunController.get_run_state(run_id).tenant_id` when only `run_id` is bound.
- **`GET /api/v1/tenant/{tenant_id}/usage`**: `llm_cost_used`, `limit` (null if quota disabled).
- **Pipeline**: no duplicate check in `EventPipeline.run`; all LLM traffic goes through `LLMClient` (including optional `INGEST_PIPELINE_LLM_ACK`).

## What Changed (Agent LLM timeline binding)
- `src/core/agent_engine.py::execute_run`: `set_llm_run_id(str(run_id))` for handler lifetime so any `LLMClient.invoke` during Kafka (or other) agent execution appends `llm_call_*` to the same RunController run; cleared in `finally`.
- `src/core/agent_scheduler.py::run_agent_and_log`: when `initial_context` includes `run_id` (as in `main.py::run_agent_v1`), binds the same context around `framework.run` so synchronous API agent runs get LLM steps on the run timeline.
- **Manual E2E:** use an agent that actually calls `get_llm_for_task` / `LLMClient` (e.g. **PatternAnalyzerAgent**, **TodayTomorrowPlannerAgent**). **InsightAgentV2** is graph/InsightsEngine-only and will not produce `llm_call_*` unless it is extended to call an LLM.

## What Changed (Direction B — LLM routing + model in run APIs)
- `src/core/llm_router.py`: cost/latency-aware `select_model`; **bulk** tasks default to route **gemma4** (Ollama + `GEMMA4_OLLAMA_MODEL` / `GEMMA4_MODEL`, default `gemma2`); **reasoning** prefers Claude when `LLM_COST_BUDGET` allows, else Groq, else Gemma; env overrides `BULK_PROVIDER` / `REASONING_PROVIDER` / etc. still force provider as before.
- `src/core/llm_client.py`: `routing_tag` + RunController step **`llm_call_<tag>`** when `llm_run_context` has `run_id`.
- `src/core/llm_run_context.py`: bind `run_id` around LLM calls.
- `src/core/pipeline.py`: optional **`INGEST_PIPELINE_LLM_ACK=1`** performs one bulk-route LLM invoke (verification / timeline demo; default off).
- `src/core/run_controller.py`: `infer_llm_route_from_steps`; **`get_recent_runs`** includes **`model`** (last LLM route suffix).
- `GET /api/v1/run/{run_id}/status` includes **`model`** (same derivation).
- Monitoring UI: **`model_used`** column on runs table + modal summary.
- Env: **`LLM_LATENCY_BUDGET`**, **`LLM_COST_BUDGET`**, **`GEMMA4_OLLAMA_MODEL`**, **`INGEST_PIPELINE_LLM_ACK`**.

### Regression tests (LLM routing / agent timeline)

- **`tests/test_agent_llm_run_context.py`** — **`AgentExecutionEngine.execute_run`** binds **`llm_run_id`** so handler-time **`LLMClient`** steps land on the same RunController run (fake Redis).
- **`tests/test_llm_usage.py`** — **`GET /api/v1/llm/usage`** auth / JSON shape when keys absent (no provider network).

## What Changed (This Step)
- Implemented Run Envelope fields on canonical events:
  - `run_id`, `workflow_type`, `idempotency_key`, `parent_run_id`
  - in `src/models/event.py` (`CanonicalEvent` serialization/deserialization).
- Added Run Envelope fields to Kafka envelope:
  - in `src/agents/kafka_event_agent.py::EventEnvelope` and emitted payload.
- Added API boundary generation and propagation for ingest:
  - in `src/main.py::ingest` generates `run_id`, `trace_id`, `workflow_type`, optional header-based `idempotency_key`.
  - returns `run_id` + `trace_id` to caller.
- Added worker-side propagation and idempotency enrichment:
  - in `src/workers/kafka_processor.py` idempotency now prefers explicit idempotency key, then event/run/trace keys.
  - canonical payload now carries run envelope fields.
- Added metadata propagation in handlers:
  - `src/core/event_registry_handlers.py`
  - `src/modules/m3/handlers.py`
- Propagated Run Envelope to remaining API paths:
  - `src/api/v1_m3.py` (reflect/synthesis/evolution now generate and return `run_id` + `trace_id`, and carry workflow_type/idempotency_key in CanonicalEvent)
  - `src/api/v1_ingestion.py` (webhook ingest helper now emits run/trace/workflow/idempotency fields)
  - `src/api/v1_events.py` (v1 create event now emits run/trace/workflow/idempotency fields and returns run/trace)
  - `src/api/agents.py` (agent run enqueue + kafka event now include `trace_id` and `workflow_type`)
  - `src/main.py` (`/api/v1/agents/{agent_id}/run` now returns run/trace and injects run envelope into context)

## Current State After Change
- Run envelope propagation now covers core ingest, v1 event creation, webhook ingest paths, M3 event creation routes, and both agent run API paths.
- Determinism improved for duplicate suppression when explicit idempotency key is supplied.
- **Superseded:** runtime step-state lives in **RunController** (Redis **`tenant:{tenant_id}:{run_id}`** + **`run_lookup:{run_id}`**), not a separate legacy-only store.

## What Changed (RunController Implementation) — historical note
- **Older documentation described only `run:{run_id}` on Redis.** **Canonical keys today** are **`tenant:{tenant_id}:{run_id}`** + **`run_lookup:{run_id}`**; legacy **`run:{run_id}`** is optional — see **RunController & Redis — single source of truth**.
- Module: **`src/core/run_controller.py`** — `RunState`, `RunController`, `get_run_controller()`, in-memory fallback when Redis is down.
- **Integrated API run creation:** `src/main.py` **`/api/v1/ingest`**, **`/api/v1/agents/{agent_id}/run`** → `create_run`.
- **Kafka:** `kafka_processor.process_event` → run steps (`kafka_received`, `idempotency_check`, `registry_dispatch`, `kafka_processed`, `kafka_failed`).
- **Full pipeline:** `EventPipeline.run` → phase steps (`pipeline_start`, `governance_check`, `qdrant_projection`, `mongo_write`, `history_write`, `schema_projection`, `pipeline_complete`).
- **Agents:** `agent_engine` → run steps (`agent_state`, `agent_execute_start`, `agent_execute_complete`).

## Current State After Implementation
- `run_id` has authoritative runtime state under **partitioned Redis** keys **`tenant:{tenant_id}:{run_id}`** (plus **`run_lookup:{run_id}`**); optional legacy read **`run:{run_id}`** when **`RUN_CONTROLLER_READ_LEGACY_KEYS=1`**.
- Step-level transitions are persisted during worker/pipeline/agent execution for integrated paths.
- **Unified run status HTTP API:** `GET /api/v1/run/{run_id}/status` in `src/main.py` returns `run_id`, `state`, `timeline` (same step entries as Redis `steps` JSON), `overall_status`, `is_complete` (true when `state` is `completed` or `failed`). In production, responses are tenant-scoped: if the run’s `tenant_id` does not match the authenticated tenant, the API returns **404** (same as unknown `run_id`). With `SKIP_AUTH=1` or local dev mode, any run may be read (dashboard convenience).
- **Tenant runs dashboard HTTP API:** `GET /api/v1/tenant/{tenant_id}/runs?limit=50` (limit capped at 200) returns recent runs for that tenant plus `stats` (`total`, `completed`, `partial`, `failed`) computed over the **returned page** only. `RunController.get_recent_runs` merges in-memory runs with Redis **`SCAN tenant:{tenant_id}:*`** (optional legacy **`run:*`** when **`RUN_CONTROLLER_SCAN_LEGACY_FOR_LIST=1`**). Path `tenant_id` must equal the authenticated tenant context or the API returns **403** (`tenant mismatch`).
- **Partial-run reconciliation:** `RunController.list_run_ids_by_state("partial")` + `EventPipeline.reconcile_run(run_id)` loads the canonical Mongo event via `EventStore.find_latest_by_run_id(tenant_id, run_id)` (`metadata.run_id`), replays failed **history** (`replay_history_for_event`) and/or **Qdrant+schema** (`run_post_ingest_for_event`), clears `history_write_failed` when repaired, appends `reconciled` / `completed` on success. `ReconciliationWorker.reconcile_partial_runs` batches this; Celery task `reconcile_partial_runs_task` is on beat **every 900s (15m)** (`scheduled` queue). Not HTTP — invoke worker/beat or `celery -A src.workers.celery_app call reconcile_partial_runs_task` for ad-hoc runs.
- **`EventPipeline.run` coverage:** all five call sites aligned with **create_run** + **`metadata.run_id`** (registry ingest/M3, Celery **`ingest_task`**, **`connector_sync`**, **`notion_sync`**).

### Regression tests (tenant runs, usage, quotas, alerting)

- **`tests/test_api_tenant_runs.py`** — **`GET /api/v1/tenant/{tenant_id}/runs`** JSON + page **`stats`** (RunController seeded; **`SKIP_AUTH`**).
- **`tests/test_api_tenant_usage.py`** — **`GET /api/v1/tenant/{tenant_id}/usage`** with mocked **`get_tenant_llm_cost_used`** / limit.
- **`tests/test_quotas.py`** — **`check_tenant_llm_budget`**, **`QuotaExceeded`**, **`get_effective_llm_quota_limit_usd`** vs **`LLM_QUOTA_LIMIT_USD`**.
- **`tests/test_alerting.py`** — **`on_run_controller_step`** hourly counters / thresholds with fake Redis.
- **`tests/test_api_tenant_alerts.py`** — **`GET /api/v1/tenant/{tenant_id}/alerts`** with mocked **`get_active_alerts`**.

## Verification Run Result (Latest)
- **history_write hardening** (`src/core/history.py`):
  - Connect uses bounded retries with backoff, per-attempt `serverSelectionTimeoutMS`, and `health_check()` via `ping`.
  - Stale connections are reset before retry; index creation runs after successful ping.
- **Pipeline failure semantics** (`src/core/pipeline.py`):
  - On history persistence failure, run step is recorded as `history_write_failed` / `failed` (not a generic `history_write` failure that is easy to misread in timelines).
  - Successful pipeline completion now emits `pipeline_start` / `completed` before `pipeline_complete`, so aggregate `state` can reach `completed` when all terminal steps succeed.
- **RunController + Redis** (`src/core/run_controller.py`):
  - **Canonical:** run documents are a **Redis hash** at **`tenant:{tenant_id}:{run_id}`** (fields include `state`, `steps` JSON, etc.), with **`run_lookup:{run_id}`** → tenant. Legacy hash **`run:{run_id}`** may still appear when **`RUN_CONTROLLER_WRITE_LEGACY_RUN_KEY`** was on or from pre-partition data; **`RUN_CONTROLLER_READ_LEGACY_KEYS`** controls read fallback.
  - Legacy string **`SET`** values remain readable where applicable (WRONGTYPE → **`GET`** JSON fallback inside the reader).
  - Redis client: **ping retries** with backoff; transient outage → **~15s backoff** before retry.
  - Aggregate **`state`**: **latest status per step name** when the same step repeats (e.g. `kafka_received` processing → completed).
- **Redis inspection (local / ops)**:
  - Example: `redis-cli HGETALL tenant:<tenant_id>:run_75c5752911fa4a6db5057f5664eb572f` and `GET run_lookup:run_75c5752911fa4a6db5057f5664eb572f` (replace `<tenant_id>` with the run’s tenant).
  - **Historical note:** older captures used **`HGETALL run:run_75c…`** only; that matches **legacy** layout, not the **canonical** key for new writes.
  - Reference capture: `tests/verification_assets/redis_hgetall_run_verification.png` (content may reflect legacy key if taken before partitioning).
- **Full-stack note:** Live `/api/v1/ingest` → Kafka → worker was not re-run here; re-run when Docker/WSL Redis integration and stack services are up.

## Regression test index (linked from this doc)

| Test file | Coverage (see **### Regression tests** in section above) |
|-----------|----------------------------------------------------------|
| **`tests/test_pipeline_run_lifecycle.py`** | Milestone — **`PIPELINE_RUN_POLICY`**, metrics, **`STRICT_RUN_BOUNDARY_FAIL_FAST`** |
| **`tests/test_run_controller.py`** | RunController & Redis — partitioned keys, aggregate **`state`** |
| **`tests/test_api_run_status.py`** | RunController & Redis — **`GET /api/v1/run/{run_id}/status`** |
| **`tests/test_reconciliation_worker.py`** | Cross-store matrix — **`reconcile_run`** / **`partial`** |
| **`tests/test_kafka_event_idempotency.py`** | Idempotency paths — **`_get_event_idempotency_key`** |
| **`tests/test_governance_engine.py`** | Governance / OPA — deny on error / allow when disabled |
| **`tests/test_core.py`** | Core — **`Event`** / **`AgentFramework`**; governance disabled with empty OPA URL |
| **`tests/test_observability_metrics.py`** | Metrics exposure — **`/observability/metrics/*`** smoke |
| **`tests/test_api_tenant_runs.py`** | Tenant runs API — **`GET /api/v1/tenant/{tenant_id}/runs`** |
| **`tests/test_api_tenant_usage.py`** | LLM usage API — **`GET /api/v1/tenant/{tenant_id}/usage`** |
| **`tests/test_quotas.py`** | Quotas core — **`LLM_QUOTA_LIMIT_USD`**, **`QuotaExceeded`** |
| **`tests/test_alerting.py`** | Alerting core — Redis counters / **`on_run_controller_step`** |
| **`tests/test_api_tenant_alerts.py`** | Alerts API — **`GET /api/v1/tenant/{tenant_id}/alerts`** |
| **`tests/test_agent_llm_run_context.py`** | Agent + LLM — **`llm_run_context`** / **`llm_call_*`** on run timeline |
| **`tests/test_llm_usage.py`** | Per-user LLM usage API — **`GET /api/v1/llm/usage`** |

## Production checklist (package verified — 2026-04-09)
| Item | Status |
|------|--------|
| Multi-tenant Redis run keys `tenant:{tenant_id}:{run_id}` + `run_lookup:{run_id}` | ✅ |
| Tenant-scoped LLM quota + **`/api/v1/tenant/{id}/usage`** | ✅ |
| Production alerting + **`/api/v1/tenant/{id}/alerts`** + dashboard badges | ✅ |
| Run monitor UI + SSE tenant runs stream | ✅ |
| **`PIPELINE_RUN_POLICY`** (warn/strict) + pipeline metrics **`kirp_pipeline_*`** | ✅ |
| **`STRICT_RUN_BOUNDARY_FAIL_FAST`** (orphan `run_id` in warn mode) | ✅ |
| Reconciliation worker + Celery beat (partial runs) | ✅ |
| **`PIPELINE_RUN_ID_REQUIRED` / `PIPELINE_RUN_STATE_MISSING`** semantics documented | ✅ |
| Grafana dashboard JSON for pipeline counters (`deploy/grafana/kirp_pipeline_dashboard.json`) | ✅ |
| **Regression test index** (doc-linked modules; table above) | ✅ |
| **CI:** GitHub Actions **`tests.yml`** runs **`pytest tests/`** on push/PR (**main**, **kirp2**); dev deps **`requirements-dev.txt`** | ✅ |
| Org-specific: TLS, secrets vault, backup DR drill, on-call runbooks | ⏳ *standard ops — execute per environment* |

## Next action (Week 6 — strategic pause)
Choose one: **A)** M3 proactive agents · **B)** Kubernetes horizontal scale · **C)** SaaS launch + Stripe billing.