## 2026-04-09

### Changed (Doc / operator traceability — go X10)
- **`tests/test_core.py`** — **`test_governance_disabled`** runs under plain **`pytest`** via **`asyncio.run`** (no skipped async test).
- **`SYSTEM_STATUS.md`** — **Last Updated** 2026-04-11; **`test_core`** regression note.
- **`docs/env.local.example`** — **`KAFKA_BOOTSTRAP_SERVERS`**, **`EMBEDDING_PROVIDER`**, **`EMBEDDING_MODEL`**.
- **`README.md`** — links to **`SYSTEM_STATUS.md`** and **`SYSTEM_ARCHITECTURE.md`**.
- **`deploy/KIRP_PRODUCTION_ONEPAGER.md`** — pointer to **`SYSTEM_STATUS.md`** as operator runbook.
- **`deploy/grafana/README.md`** — link to production one-pager.
- **`docs/QUICKSTART.md`** — **`SYSTEM_ARCHITECTURE.md`** pointer.
- **`opa_policies_live/README.md`** — pointer to **Governance / OPA** in **`SYSTEM_STATUS.md`**.

### Changed (Doc / operator traceability — go X5 round 4)
- **`SYSTEM_STATUS.md`** — Governance **### Regression tests** + index row for **`tests/test_core.py`** (Event, AgentFramework, **`GovernanceEngine(opa_url="")`**).
- **`docs/env.local.example`** — commented **`BULK_PROVIDER`**, **`REASONING_PROVIDER`**.
- **`SYSTEM_ARCHITECTURE.md`** — pointer to **`SYSTEM_STATUS.md`** for keys, metrics, regression index, post-ingest semantics.

### Changed (Doc / operator traceability — go X5 round 3)
- **`SYSTEM_STATUS.md`** — **### Regression tests (LLM routing / agent timeline)**; index rows for **`test_agent_llm_run_context`**, **`test_llm_usage`**.
- **`docs/env.local.example`** — commented **`LLM_LATENCY_BUDGET`**, **`LLM_COST_BUDGET`**, **`GEMMA4_OLLAMA_MODEL`**, **`INGEST_PIPELINE_LLM_ACK`**.
- **`deploy/prometheus.yml`** — comment cross-reference to **`SYSTEM_STATUS.md`** (metrics path / **`DISABLE_PROMETHEUS`**).

### Changed (Doc / operator traceability — go X5 round 2)
- **`SYSTEM_STATUS.md`** — **Last Updated** 2026-04-10; **### Regression tests** for tenant runs, usage, quotas, alerting; **Regression test index** rows for **`test_api_tenant_runs`**, **`test_api_tenant_usage`**, **`test_quotas`**, **`test_alerting`**, **`test_api_tenant_alerts`**.
- **`docs/env.local.example`** — commented **`ALERT_COUNTER_TTL_SEC`** / **`ALERT_ACTIVE_TTL_SEC`**.
- **`docs/QUICKSTART.md`** — pointer to **`SYSTEM_STATUS.md`** for English ops / regression index.

### Changed (Doc / operator traceability — controlled execution)
- **`SYSTEM_STATUS.md`** — RunController source-of-truth, cross-store failure matrix, idempotency paths, Governance/OPA, metrics exposure, per-section **### Regression tests**, consolidated **Regression test index** table; production checklist row for that index.
- **`docs/env.local.example`** — backend env hints: pipeline policy, RunController Redis flags, Prometheus, OPA, LLM quota, alerting.
- **Tests added:** `tests/test_governance_engine.py`, `tests/test_observability_metrics.py`, `tests/test_kafka_event_idempotency.py`.

### Added (Operations package)
- `deploy/grafana/kirp_pipeline_dashboard.json` + `deploy/grafana/README.md` — Grafana panels for **`kirp_pipeline_no_run_id_total`** / **`kirp_pipeline_orphan_run_id_total`** (rate + 1h increases).
- `deploy/KIRP_PRODUCTION_ONEPAGER.md` — internal GTM / SE one-pager ($10K MRR framing).
- `deploy/prometheus.yml` — **`kirp-api`** scrape path **`/observability/metrics/prometheus`** (OpenMetrics text for counters).
- `SYSTEM_STATUS.md` — milestone **100% EventPipeline.run lifecycle**, production checklist table, Week 6 pause.

### Added (EventPipeline.run lifecycle visibility — Phase 1)
- `src/core/pipeline.py` — **`PIPELINE_NO_RUN_ID`** warning + counter **`kirp_pipeline_no_run_id_total`** `{event_type, source}` when `metadata.run_id` is absent (pipeline still runs). **`PIPELINE_ORPHAN_RUN_ID`** error + **`kirp_pipeline_orphan_run_id_total`** when `run_id` is set but RunController has no state; **`STRICT_RUN_BOUNDARY_FAIL_FAST=1`** raises **`RunStateMissing`** (`ValueError` subclass). Metrics no-op when `DISABLE_PROMETHEUS=1` or `prometheus_client` missing.
- `tests/test_pipeline_run_lifecycle.py` — log + metric assertions.

### Changed (EventPipeline.run — Phase 2 strict policy)
- **`PIPELINE_RUN_POLICY`**: `warn` (default) or `strict`. In **`strict`**, missing `metadata.run_id` raises **`RunStateMissing("PIPELINE_RUN_ID_REQUIRED")`** (after warning + metric); orphan `run_id` raises **`RunStateMissing("PIPELINE_RUN_STATE_MISSING")`**. In **`warn`**, orphan + **`STRICT_RUN_BOUNDARY_FAIL_FAST=1`** still raises the legacy **`run_missing_state`** message. Invalid policy values log a warning and fall back to **`warn`**.
- **`connector_sync`**, **`notion_sync`**, **`ingest_task`**: when payload metadata has no `run_id`, call **`RunController.create_run`** and inject **`run_id`** / **`trace_id`** / **`workflow_type`** so **`PIPELINE_RUN_POLICY=strict`** works for background ingests.

### Changed (Multi-tenant Redis run keys)
- `RunController` — canonical Redis hash key **`tenant:{tenant_id}:{run_id}`** plus **`run_lookup:{run_id}`** → `tenant_id` for resolution when callers only have `run_id`. Optional legacy read **`run:{run_id}`** when **`RUN_CONTROLLER_READ_LEGACY_KEYS=1`** (default on for migration); optional dual-write with **`RUN_CONTROLLER_WRITE_LEGACY_RUN_KEY=1`** (default off).
- **`RunController.update_key_prefix(tenant_id)`** — Kafka/worker hint so `get_run_state(run_id)` resolves the correct partition without passing `tenant_id` on every call.
- **`GET /api/v1/run/{run_id}/status`** — passes authenticated tenant as `tenant_id` hint to `get_run_status` (partition read + same 404-on-mismatch behavior).
- **`EventPipeline`**, **`LLMClient`**, **`kafka_processor`** — pass explicit `tenant_id` or call `update_key_prefix` per message so pipeline/LLM quota resolution stays tenant-scoped.
- **Two-tenant example:** Tenant A run → Redis key `tenant:tenant_a:{run_id}`; Tenant B run → `tenant:tenant_b:{run_id}` (separate hashes). LLM quota / alerting keys remain **`tenant:{tenant_id}:llm_cost`**, **`tenant:{tenant_id}:alert:...`**.

### Added (Production alerting)
- `src/core/alerting.py` — `on_run_controller_step` / `Alerting.check_run_alerts`, Redis hourly counters `tenant:{id}:alert:h:{YYYYMMDDHH}:failures|successes`, active list `tenant:{id}:alerts:active`; **≥ `ALERT_FAILURES_PER_HOUR`** (default 5) failed steps/hour → `hourly_failures` alert; **failure rate** `failures/(failures+successes)` &gt; `ALERT_FAILURE_RATE_THRESHOLD` (default 0.2) with min samples `ALERT_MIN_SAMPLES_FOR_RATE` (default 10) → `high_failure_rate`; optional `ALERT_SLACK_WEBHOOK_URL` (httpx POST); email path = structured **ERROR** log (no SMTP in core).
- `RunController.update_step` — after persist, calls `on_run_controller_step` (failures + terminal successes: `pipeline_complete`, `agent_execute_complete`, `kafka_processed`).
- `GET /api/v1/tenant/{tenant_id}/alerts` — `{ tenant_id, alerts, count }`, **403** on tenant mismatch.
- Dashboard: Run monitor title **alert badge**; SideNav **Run monitor** amber dot when `count > 0`; `getTenantAlertsV1` in `lib/apiClient.ts`.
- Tests: `tests/test_alerting.py`, `tests/test_api_tenant_alerts.py`.

### Added (Production LLM quotas)
- `src/core/quotas.py` — `TenantQuota`, `QuotaExceeded`, Redis key `tenant:{tenant_id}:llm_cost` (INCRBYFLOAT), TTL `LLM_QUOTA_COUNTER_TTL_SEC` (default 45d); `check_tenant_llm_budget` / `increment_tenant_llm_cost` / `get_tenant_llm_cost_used`; enforcement when **`LLM_QUOTA_LIMIT_USD` > 0** (unset = unlimited).
- `LLMClient.invoke` — resolves tenant from `llm_tenant_id` context or RunController `run_id`; pre-call ceiling via `estimate_call_ceiling_usd`; post-success `increment_tenant_llm_cost`.
- `src/core/cost_tracker.py` — `estimate_call_ceiling_usd`, `ollama` nominal rates for quota math.
- `src/core/llm_run_context.py` — `llm_tenant_id` context (set in `execute_run`, scheduler, `/api/v1/ask`).
- `GET /api/v1/tenant/{tenant_id}/usage` — `llm_cost_used`, `limit` (or `null` if quota off); **403** tenant mismatch.
- FastAPI handler for `QuotaExceeded` → **429** JSON `detail`, `llm_cost_used`, `limit`, `estimated_cost`.
- `AgentScheduler` — re-raises `QuotaExceeded` so API returns 429 (not swallowed into `{ok: false}`).
- Tests: `tests/test_quotas.py`, `tests/test_api_tenant_usage.py`.

### Added (Agent binding — llm_run_context)
- `AgentExecutionEngine.execute_run` (`src/core/agent_engine.py`) sets `llm_run_context` for `str(run_id)` for the whole handler (Kafka `agent_run` + any direct `execute_run` caller); resets in `finally`.
- `AgentScheduler.run_agent_and_log` (`src/core/agent_scheduler.py`) binds the same when `initial_context["run_id"]` is set (covers `POST /api/v1/agents/{id}/run`, which passes RunController `run_id` in context).
- `tests/test_agent_llm_run_context.py` — binding + reset on success/failure; scheduler binding when `run_id` present.

### Added (Direction B — Gemma / LLM routing visibility)
- `src/core/llm_router.py` — `ROUTING_PROFILES` (cost/latency metadata), `select_model` / `best_provider`, bulk default route **gemma4** (Ollama model from `GEMMA4_OLLAMA_MODEL` / `GEMMA4_MODEL`, default `gemma2`); reasoning respects `LLM_COST_BUDGET` / `LLM_LATENCY_BUDGET`; legacy `BULK_PROVIDER` / `REASONING_PROVIDER` env overrides unchanged.
- `src/core/llm_run_context.py` — contextvar to bind a `run_id` while `LLMClient.invoke` runs so RunController gets `llm_call_<route>` steps.
- `LLMClient` (`src/core/llm_client.py`) — optional `routing_tag`; after each invoke appends timeline step when context `run_id` is set.
- `GET /api/v1/tenant/.../runs` rows and `GET /api/v1/run/{id}/status` — `model` field = last `llm_call_*` suffix (`infer_llm_route_from_steps` in `run_controller.py`).
- Optional ingest verification: `INGEST_PIPELINE_LLM_ACK=1` runs one bulk-routed LLM call during `EventPipeline.run` (for `llm_call_gemma4` in timeline when Ollama/Gemma is up).
- Dashboard: `RunsTable` **model_used** column; `RunDetailModal` shows `model_used` when present; `lib/apiClient.ts` types updated.
- Tests: tenant runs + run status assert `model` / `llm_call_gemma4` timeline.

### Added
- Next.js **Run monitor** (`app/(dashboard)/monitoring/page.tsx`): tenant runs list + stats pie + row click → modal timeline; `lib/apiClient.ts` — `getTenantRunsV1`, `getRunStatusV1`; `lib/hooks/useTenantRunsStream.ts` — SSE over fetch with `Authorization`; components under `components/monitoring/`; SideNav link **Run monitor** → `/monitoring`.
- FastAPI `GET /api/v1/tenant/{tenant_id}/runs/stream` — `text/event-stream` JSON snapshots every 15s (same payload shape as GET `/runs`).
- `src/workers/reconciliation_worker.py` — `ReconciliationWorker` batch-reconciles partial runs via `EventPipeline.reconcile_run`.
- Celery `reconcile_partial_runs_task` in `src/workers/tasks.py` + beat entry `reconcile-partial-runs-15m` (900s) in `src/workers/celery_app.py`.
- `EventPipeline.replay_history_for_event`, `reconcile_run`, `_last_step_status_map`.
- `EventStore.find_latest_by_run_id` — resolve ingest event by `metadata.run_id` + `tenant_id`.
- `RunController.list_run_ids_by_state` — SCAN + in-memory listing by aggregate state.
- `tests/test_reconciliation_worker.py` — partial → completed after mocked history replay; `list_run_ids_by_state`.
- `GET /api/v1/tenant/{tenant_id}/runs` in `src/main.py` — tenant dashboard: recent runs + page-level `stats`; **403** if path tenant ≠ authenticated tenant.
- `RunController.get_recent_runs(tenant_id, limit)` — in-memory + Redis `SCAN run:*`, filter by tenant, sort by `started_at` desc; each run summary includes `run_id`, `state`, `started_at`, `steps_count`, `workflow_type`, `trace_id`.
- `tests/test_api_tenant_runs.py` — 200 ordering/stats, 403 mismatch, `limit` slice.
- `GET /api/v1/run/{run_id}/status` in `src/main.py` — JSON lifecycle view (`state`, `timeline`, `overall_status`, `is_complete`) backed by `RunController`; tenant isolation when auth is enabled.
- `tests/test_api_run_status.py` — 200/404 coverage with seeded `RunController`.
- `tests/test_run_controller.py`: aggregate state uses last status per step name; hash field round-trip for `RunState`.
- `tests/verification_assets/redis_hgetall_run_verification.png`: visual capture of `HGETALL` proof session (local Redis :16379).
- Production-hardening baseline analysis captured in `SYSTEM_STATUS.md`:
  - code-based architecture map (ingestion -> pipeline -> agents -> memory -> output),
  - determinism breakpoints,
  - inconsistency points,
  - duplicated logic map,
  - top 5 production-critical weaknesses.
- Single active hardening focus defined:
  - unified Run Envelope propagation (`run_id`, `workflow_type`, `idempotency_key`, `parent_run_id`).
- Single next move defined with exact target files.
- Run Envelope fields added to canonical model:
  - `run_id`, `workflow_type`, `idempotency_key`, `parent_run_id` in `src/models/event.py`.
- Kafka envelope propagation fields added in `src/agents/kafka_event_agent.py`.
- API ingest now emits run/trace context in `src/main.py::ingest`.
- Worker propagation/idempotency enrichment added in `src/workers/kafka_processor.py`:
  - idempotency key preference: explicit idempotency key -> event id -> run id -> trace id -> hash.
- Handler metadata propagation for run envelope added in:
  - `src/core/event_registry_handlers.py`
  - `src/modules/m3/handlers.py`
- Run envelope propagation to remaining paths:
  - `src/api/v1_m3.py`:
    - `_canonical_m3_event` now accepts run envelope fields,
    - `/m3/reflect`, `/m3/synthesis`, `/m3/evolution` now generate and return `run_id` + `trace_id`.
  - `src/api/v1_ingestion.py`:
    - `_ingest_one` now emits `run_id`, `trace_id`, `workflow_type`, `idempotency_key`.
  - `src/api/v1_events.py`:
    - `POST /api/v1/events` now emits and returns run/trace envelope fields.
  - `src/api/agents.py`:
    - `POST /api/agents/{agent_id}/run` now includes `trace_id`/`workflow_type` in kafka agent_run payload and response.
  - `src/main.py`:
    - `POST /api/v1/agents/{agent_id}/run` now injects run envelope into context and returns run/trace.
- Approved next implementation target documented (no runtime code yet):
  - `src/core/run_controller.py` authoritative run-state machine with Redis-backed `run:{run_id}` state,
  - integrations planned for `main.py`, `kafka_processor.py`, `pipeline.py`, `agent_engine.py`.
- Implemented `src/core/run_controller.py`:
  - `RunState` model
  - `create_run`, `update_step`, `get_run_status`
  - Redis-backed storage (`run:{run_id}`) with in-memory fallback.
- Integrated RunController into runtime paths:
  - `src/main.py` (`/api/v1/ingest`, `/api/v1/agents/{agent_id}/run`)
  - `src/workers/kafka_processor.py` step transitions
  - `src/core/pipeline.py` per-phase projection transitions
  - `src/core/agent_engine.py` agent runtime transitions mirrored to run steps.
- Verification run documentation added with concrete run_id and step timeline:
  - `RUN_LEDGER.md` entry `run_2026_04_09_verification_runcontroller`
  - includes partial status, failure step, and environment constraints.

### Changed
- `src/core/config.py`: removed broken duplicate `Settings` class that referenced `SettingsConfigDict` when `pydantic-settings` is missing; single class is now `Settings = _settings_base()` (unblocks `import src.main` in tests).
- `src/core/history.py`: Mongo connect retries with backoff, `health_check()`, connection reset on stale ping failures, `serverSelectionTimeoutMS` on client.
- `src/core/pipeline.py`: history failure step renamed to `history_write_failed`; emit `pipeline_start` / `completed` before `pipeline_complete`.
- `src/core/run_controller.py`: Redis **hash** storage for `run:{run_id}` (`state`, `steps`, metadata fields), legacy string key fallback; ping retries + 15s backoff on failure; `redis_health()`; aggregate state dedupes by latest step name.
- `SYSTEM_STATUS.md` / `RUN_LEDGER.md`: documented Redis HGETALL proof and history_write hardening.
- `SYSTEM_STATUS.md` converted from placeholder template to actual current-system status.
- `RUN_LEDGER.md` normalized to include control-plane baseline run and explicit step outcomes.
- `SYSTEM_STATUS.md` updated to reflect implemented run envelope propagation status.
- `RUN_LEDGER.md` updated with implementation run and step outcomes.
- `SYSTEM_STATUS.md` updated to reflect expanded run-envelope coverage and the new next gap (runtime step-state persistence).
- `RUN_LEDGER.md` updated with SAFE AUTONOMY propagation run and exact touched paths.
- `SYSTEM_STATUS.md` updated with explicit STOP MODE gate and approved-next-move scope.
- `RUN_LEDGER.md` updated with approval checkpoint run entry.
- `SYSTEM_STATUS.md` updated to reflect completed RunController integration and new remaining gap.
- `RUN_LEDGER.md` updated with implementation run details and touched files.
- `SYSTEM_STATUS.md` updated with latest verification outcome and exact failed phase (`history_write`).
- `RUN_LEDGER.md` updated with full observed timeline for one run_id.

### Notes
- Run Envelope propagation is implemented for core ingest path; next is expanding uniform run-state lifecycle persistence across all workflow entrypoints.
- Current step executed in STOP MODE: status/log updates only, no runtime behavior changes.
- Current step executed after approval: runtime control-layer implementation completed for core files.
- Latest verification confirms RunController step tracking works, but Redis single-source proof is blocked in this environment (Redis unavailable).