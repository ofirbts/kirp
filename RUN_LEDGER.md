## Active Runs

### run_2026_04_11_go_x10_doc_test_readme_ops
- workflow_type: production_readiness_docs
- status: completed
- trace_id: tr_go_x10_20260411
- owner: cursor
- mode: SAFE_AUTONOMY
- scope:
  - test_core_asyncio_run_no_skip
  - env_kafka_embedding_hints
  - readme_quickstart_onepager_grafana_opa_status_crosslinks
- code_changes:
  - `tests/test_core.py`
  - `SYSTEM_STATUS.md`
  - `docs/env.local.example`
  - `README.md`
  - `deploy/KIRP_PRODUCTION_ONEPAGER.md`
  - `deploy/grafana/README.md`
  - `docs/QUICKSTART.md`
  - `opa_policies_live/README.md`
  - `CHANGELOG.md`
  - `RUN_LEDGER.md`
- verification: pytest `tests/test_core.py`

### run_2026_04_10_go_x5_round4_core_arch_pointer
- workflow_type: production_readiness_docs
- status: completed
- trace_id: tr_go_x5_r4_20260410
- owner: cursor
- mode: SAFE_AUTONOMY
- scope:
  - SYSTEM_STATUS_test_core_governance_regression
  - env_example_bulk_reasoning_provider
  - SYSTEM_ARCHITECTURE_STATUS_pointer
- code_changes:
  - `SYSTEM_STATUS.md` — `test_core` under Governance + index
  - `docs/env.local.example` — `BULK_PROVIDER` / `REASONING_PROVIDER`
  - `SYSTEM_ARCHITECTURE.md` — SYSTEM_STATUS cross-link
  - `CHANGELOG.md` — round 4 note
  - `RUN_LEDGER.md` — this entry
- verification: pytest `tests/test_core.py`

### run_2026_04_10_go_x5_round3_llm_regression_docs
- workflow_type: production_readiness_docs
- status: completed
- trace_id: tr_go_x5_r3_20260410
- owner: cursor
- mode: SAFE_AUTONOMY
- scope:
  - SYSTEM_STATUS_llm_agent_regression_section_and_index
  - env_example_llm_routing_vars
  - prometheus_yml_doc_comment
- code_changes:
  - `SYSTEM_STATUS.md` — LLM/agent regression bullets + index rows
  - `docs/env.local.example` — Direction B env hints
  - `deploy/prometheus.yml` — SYSTEM_STATUS pointer
  - `CHANGELOG.md` — round 3 note
  - `RUN_LEDGER.md` — this entry
- verification: pytest `tests/test_agent_llm_run_context.py` `tests/test_llm_usage.py`

### run_2026_04_10_go_x5_round2_tenant_alerts_index
- workflow_type: production_readiness_docs
- status: completed
- trace_id: tr_go_x5_r2_20260410
- owner: cursor
- mode: SAFE_AUTONOMY
- scope:
  - SYSTEM_STATUS_regression_index_tenant_quota_alert_tests
  - env_example_alert_ttls
  - QUICKSTART_SYSTEM_STATUS_pointer
- code_changes:
  - `SYSTEM_STATUS.md` — new regression subsection + five index rows
  - `docs/env.local.example` — `ALERT_*_TTL_SEC` comments
  - `docs/QUICKSTART.md` — ops pointer
  - `CHANGELOG.md` — this batch note
  - `RUN_LEDGER.md` — this entry
- verification: pytest `tests/test_api_tenant_runs.py` `tests/test_api_tenant_usage.py` `tests/test_quotas.py` `tests/test_alerting.py` `tests/test_api_tenant_alerts.py`

### run_2026_04_10_controlled_execution_doc_tests
- workflow_type: production_readiness_docs
- status: completed
- trace_id: tr_controlled_exec_docs_20260410
- owner: cursor
- mode: SAFE_AUTONOMY
- scope:
  - SYSTEM_STATUS_sections_and_regression_index
  - env_local_example_backend_parity
  - focused_regression_tests_governance_metrics_kafka_idempotency
- code_changes:
  - `SYSTEM_STATUS.md` — failure matrix, idempotency, OPA, metrics, regression bullets + index table + checklist row
  - `docs/env.local.example` — `SKIP_AUTH`, `DISABLE_PROMETHEUS`, `OPA_URL`, quotas, alerts, pipeline policy
  - `tests/test_governance_engine.py`, `tests/test_observability_metrics.py`, `tests/test_kafka_event_idempotency.py`
- verification: pytest on new modules; doc links match test files listed in **Regression test index**

### run_2026_04_09_multi_tenant_redis_partition
- workflow_type: multi_tenant_scale
- status: completed
- trace_id: tr_redis_partition_20260409
- owner: cursor
- mode: SAFE_AUTONOMY
- scope:
  - run_controller_partition_keys
  - worker_tenant_hint_update_key_prefix
  - api_status_tenant_hint
- code_changes:
  - `src/core/run_controller.py` — `tenant:{tenant_id}:{run_id}`, `run_lookup:{run_id}`, env toggles for legacy read/write/scan
  - `src/main.py` — `GET /api/v1/run/{run_id}/status` passes auth tenant to `get_run_status`
  - `src/workers/kafka_processor.py` — `update_key_prefix` before `create_run` / ingest / `agent_run`
  - `src/core/pipeline.py`, `src/core/llm_client.py` — explicit `tenant_id` on `get_run_state` where available
- verification:
  - **Two-tenant Redis keys (example):** `tenant:tenant_a:run_xyz` vs `tenant:tenant_b:run_xyz` — separate hashes; same `run_id` string is allowed per tenant without collision in Redis.
  - **`curl /api/v1/tenant/tenant_a/usage`** — still only tenant A’s `llm_cost` / quota (unchanged key layout).
- tests: `tests/test_run_controller.py::test_partitioned_redis_keys_two_tenants`

### run_2026_04_09_frontend_run_monitor
- workflow_type: product_ui
- status: completed
- trace_id: tr_run_monitor_ui_20260409
- owner: cursor
- mode: SAFE_AUTONOMY
- scope:
  - nextjs_monitoring_page
  - run_status_modal
  - sse_tenant_runs_stream_backend
- code_changes:
  - `app/(dashboard)/monitoring/page.tsx`
  - `components/monitoring/RunStatsPie.tsx`, `RunsTable.tsx`, `RunDetailModal.tsx`
  - `lib/apiClient.ts` — run monitoring types + API helpers
  - `lib/hooks/useTenantRunsStream.ts`
  - `components/navigation/SideNav.tsx` — `/monitoring` nav item
  - `src/main.py` — `GET /api/v1/tenant/{tenant_id}/runs/stream`
- verification:
  - **URL:** `http://localhost:3100/monitoring?tenant=default` (this repo’s `npm run dev` binds **3100**, not 3000; use `-p 3000` if you need that port).
  - Requires `NEXT_PUBLIC_API_URL` pointing at the FastAPI host (e.g. `http://localhost:8000`) and a valid JWT (or `SKIP_AUTH` / `NEXT_PUBLIC_SKIP_AUTH` aligned with API).
- screenshot_note: synthetic asset generation was skipped/timeout; validate visually in browser.

---

### run_2026_04_09_reconciliation_worker
- workflow_type: control_layer_hardening
- status: completed
- trace_id: tr_reconciliation_20260409
- owner: cursor
- mode: SAFE_AUTONOMY
- scope:
  - reconciliation_worker_module
  - pipeline_reconcile_run_history_projections
  - celery_beat_15m
  - event_store_find_by_run_id
- code_changes:
  - `src/workers/reconciliation_worker.py`
  - `src/workers/tasks.py` — `reconcile_partial_runs_task`
  - `src/workers/celery_app.py` — route + `reconcile-partial-runs-15m` (900s)
  - `src/core/pipeline.py` — `reconcile_run`, `replay_history_for_event`
  - `src/core/event_store.py` — `find_latest_by_run_id`
  - `src/core/run_controller.py` — `list_run_ids_by_state`
  - `tests/test_reconciliation_worker.py`
- scheduling:
  - Requires Celery worker + beat; ad-hoc: `celery -A src.workers.celery_app call reconcile_partial_runs_task` (optional kwargs `max_runs`).
- get_run_status_before_after (run_id `run_75c5752911fa4a6db5057f5664eb572f`, simulated partial with `history_write_failed` / `failed` then reconcile with Mongo event present):
  - **Before:** `state`: `partial`; latest per step: `history_write_failed` → `failed`, `history_write` absent.
  - **After:** `state`: `completed`; latest per step: `history_write` → `completed`, `history_write_failed` → `completed` (superseded via reconciliation), `reconciled` → `completed`.
- sample_verification_command_output (aggregate fields only):
```
=== BEFORE ===
{
  "state": "partial",
  "last_steps": {
    "history_write": null,
    "history_write_failed": "failed"
  }
}
=== AFTER ===
{
  "state": "completed",
  "history_write": "completed",
  "history_write_failed": "completed",
  "reconciled": "completed"
}
```

---

### run_2026_04_09_tenant_runs_dashboard_api
- workflow_type: control_layer_hardening
- status: completed
- trace_id: tr_tenant_runs_api_20260409
- owner: cursor
- mode: SAFE_AUTONOMY
- scope:
  - get_api_v1_tenant_tenant_id_runs
  - run_controller_get_recent_runs_scan
  - tests_tenant_mismatch_403
- code_changes:
  - `src/main.py` — `GET /api/v1/tenant/{tenant_id}/runs`
  - `src/core/run_controller.py` — `get_recent_runs`
  - `tests/test_api_tenant_runs.py`
- curl_example:
  - `curl -sS "http://localhost:8000/api/v1/tenant/default/runs?limit=10"` (with valid JWT for `default`, or `SKIP_AUTH=1` locally).
- sample_response_body (TestClient; matches curl JSON shape):
```json
{
  "tenant_id": "default",
  "runs": [
    {
      "run_id": "run_1",
      "state": "completed",
      "started_at": "2026-01-03T00:00:00+00:00",
      "steps_count": 1,
      "workflow_type": "ingest",
      "trace_id": null
    },
    {
      "run_id": "run_2",
      "state": "partial",
      "started_at": "2026-01-02T00:00:00+00:00",
      "steps_count": 1,
      "workflow_type": "ingest",
      "trace_id": null
    },
    {
      "run_id": "run_3",
      "state": "failed",
      "started_at": "2026-01-01T00:00:00+00:00",
      "steps_count": 1,
      "workflow_type": "ingest",
      "trace_id": null
    }
  ],
  "stats": {
    "total": 3,
    "completed": 1,
    "partial": 1,
    "failed": 1
  }
}
```
- implementation_notes:
  - Stats are for the **current page** (`limit` slice), not global tenant totals.
  - Redis uses `SCAN` with `match=run:*`; tenant filter uses hash field `tenant_id` after `get_run_state`.

---

### run_2026_04_09_unified_run_status_api
- workflow_type: control_layer_hardening
- status: completed
- trace_id: tr_run_status_api_20260409
- owner: cursor
- mode: SAFE_AUTONOMY
- scope:
  - add_get_api_v1_run_run_id_status
  - tenant_match_or_404_when_auth_enabled
  - tests_and_config_import_fix
- code_changes:
  - `src/main.py` — `GET /api/v1/run/{run_id}/status`
  - `src/core/config.py` — `Settings = _settings_base()` (fix test/app import without pydantic-settings)
  - `tests/test_api_run_status.py`
- verification:
  - **curl (when API is up on port 8000):**
    - `curl -sS "http://localhost:8000/api/v1/run/run_75c5752911fa4a6db5057f5664eb572f/status"`
    - With JWT auth enabled, send a valid token for the same `tenant_id` stored on the run; with local dev, `SKIP_AUTH=1` allows read without a token.
  - **This environment:** no listener on `:8000`; validated via `TestClient` + seeded `RunController` (same JSON shape as curl).
- sample_response_body (abbreviated `timeline`; full list matches Redis `steps` field order and content for that run):
```json
{
  "run_id": "run_75c5752911fa4a6db5057f5664eb572f",
  "state": "completed",
  "timeline": [
    {"step": "api_accepted", "status": "accepted", "error": null, "ts": "2026-04-09T17:32:08.125823+00:00"},
    {"step": "history_write", "status": "completed", "error": null, "ts": "2026-04-09T17:32:08.125836+00:00"},
    {"step": "pipeline_start", "status": "completed", "error": null, "ts": "2026-04-09T17:32:08.125847+00:00"},
    {"step": "pipeline_complete", "status": "completed", "error": null, "ts": "2026-04-09T17:32:08.125855+00:00"}
  ],
  "overall_status": "completed",
  "is_complete": true
}
```
- redis_parity_note: `timeline` is the parsed JSON array from Redis hash field `steps` (same objects as `HGETALL` → `steps`).

---

### run_2026_04_09_history_write_redis_hardening
- workflow_type: control_layer_hardening
- status: completed (code + local Redis proof; full Docker E2E not executed)
- trace_id: tr_history_redis_20260409
- owner: cursor
- mode: SAFE_AUTONOMY
- scope:
  - history_store_connect_retry_health
  - pipeline_history_write_failed_step
  - run_controller_redis_hash_hgetall
  - pipeline_pipeline_start_completed_for_aggregate_state
- code_changes:
  - `src/core/history.py` — retries, ping health, reset on failure
  - `src/core/pipeline.py` — `history_write_failed`; `pipeline_start` completed before `pipeline_complete`
  - `src/core/run_controller.py` — Redis HASH + ping/backoff + latest-per-step aggregate state
  - `tests/test_run_controller.py` — unit coverage
- redis_single_source_check:
  - **PASSED (local)** using `redis-server --port 16379` and `REDIS_URL=redis://127.0.0.1:16379/0` (Docker CLI unavailable in WSL; use `docker compose up redis` on hosts where Docker works).
  - Redis key: `run:run_75c5752911fa4a6db5057f5664eb572f` (prefix `run:` + full `run_id` including `run_`).
- redis_cli_transcript (verbatim `HGETALL`, representative run):
```
$ redis-cli -p 16379 HGETALL "run:run_75c5752911fa4a6db5057f5664eb572f"
state
completed
trace_id
trace_1
workflow_type
ingest
cost
0.0
steps
[{"step": "api_accepted", "status": "accepted", "error": null, "ts": "..."}, ..., {"step": "history_write", "status": "completed", "error": null, "ts": "..."}, ..., {"step": "kafka_processed", "status": "completed", "error": null, "ts": "..."}]
idempotency_key

run_id
run_75c5752911fa4a6db5057f5664eb572f
updated_at
2026-04-09T17:18:47.106855+00:00
started_at
2026-04-09T17:18:47.088610+00:00
tenant_id
tenant_demo
```
- screenshot_asset: `tests/verification_assets/redis_hgetall_run_verification.png`
- mongo_history_note:
  - With Mongo up, `history_write` should reach `completed` after retries; on persistent failure the timeline shows **`history_write_failed`** / `failed` with `error` populated.

---

### run_2026_04_09_verification_runcontroller
- workflow_type: verification_e2e
- status: partial
- trace_id: tr_mock
- owner: cursor
- mode: SAFE_AUTONOMY (verification only)
- run_id: run_75c5752911fa4a6db5057f5664eb572f
- execution_notes:
  - Docker services are unavailable in this environment.
  - Redis is unreachable (`redis:6379`) so RunController used in-memory fallback.
  - Verification used real `RunController` + real `EventPipeline` + real `AgentExecutionEngine` integration points.
- observed_timeline:
  - api_accepted (accepted)
  - kafka_received (processing)
  - kafka_processed (completed)
  - pipeline_start (processing)
  - governance_check (completed)
  - qdrant_projection (completed)
  - mongo_write (completed)
  - history_write (failed)
  - schema_projection (completed)
  - pipeline_complete (completed)
  - pipeline_start (processing)        # m3 event pass
  - governance_check (completed)
  - qdrant_projection (completed)
  - mongo_write (completed)
  - history_write (failed)
  - schema_projection (completed)
  - pipeline_complete (completed)
  - agent_execute_start (completed)
  - agent_state:completed (completed)
- failure_detail:
  - step: history_write
  - reason: `localhost:27017 connection refused` from `src/core/history.py` store connect.
- redis_single_source_check:
  - FAILED in this environment (Redis unreachable), so `run:{run_id}` was not readable from Redis.
  - Run status remained available in controller in-memory state for this process.

---

### run_2026_04_09_run_controller_runtime_impl
- workflow_type: control_layer_hardening
- status: completed
- trace_id: tr_run_controller_runtime_20260409
- owner: cursor
- mode: STOP_MODE_APPROVED_EXECUTION
- scope:
  - create_run_controller_module
  - integrate_main_entrypoints
  - integrate_kafka_worker_steps
  - integrate_pipeline_projection_steps
  - integrate_agent_runtime_steps
- steps:
  - add_src_core_run_controller ✅
  - wire_main_ingest_and_agent_run ✅
  - wire_kafka_processor_step_updates ✅
  - wire_pipeline_step_updates ✅
  - wire_agent_engine_step_updates ✅
  - update_feedback_files ✅
- result:
  - runtime_code_changes: 5 files modified + 1 file added
  - feedback_files_updated: 3
  - remaining_scope: unified_read_api_for_run_status_and_full_entrypoint_coverage

---

### run_2026_04_09_run_controller_approval_checkpoint
- workflow_type: control_layer_planning
- status: completed
- trace_id: tr_run_controller_approval_20260409
- owner: cursor
- mode: STOP_MODE
- scope:
  - capture_approved_next_move
  - update_feedback_files_only
  - hold_runtime_changes
- steps:
  - update_system_status_with_approved_scope ✅
  - update_changelog_with_execution_gate ✅
  - update_run_ledger_checkpoint ✅
- result:
  - runtime_code_changes: 0
  - feedback_files_updated: 3
  - pending_execution: run_controller_runtime_implementation

---

### run_2026_04_09_safe_autonomy_remaining_paths
- workflow_type: control_layer_hardening
- status: completed
- trace_id: tr_run_envelope_remaining_20260409
- owner: cursor
- mode: SAFE_AUTONOMY
- scope:
  - m3_api_event_generation
  - webhook_ingest_event_generation
  - v1_events_ingest_generation
  - agent_run_api_event_generation
  - manual_agent_run_response_context
- steps:
  - propagate_m3_run_trace_fields ✅
  - propagate_webhook_ingest_run_trace_fields ✅
  - propagate_v1_events_run_trace_fields ✅
  - propagate_agents_api_run_trace_fields ✅
  - update_feedback_files ✅
- result:
  - runtime_code_changes: 5 files
  - feedback_files_updated: 3
  - remaining_scope: runtime_step_state_persistence_by_run_id

---

### run_2026_04_09_run_envelope_ingest_impl
- workflow_type: control_layer_hardening
- status: completed
- trace_id: tr_run_envelope_ingest_20260409
- owner: cursor
- scope:
  - canonical_event_fields
  - api_ingest_envelope
  - kafka_envelope_propagation
  - worker_idempotency_enrichment
  - handler_metadata_propagation
- steps:
  - update_models_event_canonical_fields ✅
  - update_kafka_event_envelope ✅
  - update_main_ingest_boundary ✅
  - update_worker_idempotency_key_logic ✅
  - update_handler_metadata_propagation ✅
  - update_feedback_files ✅
- result:
  - runtime_code_changes: 6 files
  - feedback_files_updated: 3
  - path_covered: api_ingest_to_pipeline
  - remaining_scope: agent_run_and_m3_entrypoint_run_state_lifecycle

---

### run_2026_04_09_baseline_hardening_analysis
- workflow_type: system_analysis
- status: completed
- trace_id: tr_baseline_hardening_20260409
- owner: cursor
- scope:
  - ingestion path
  - pipeline consistency
  - agent execution path
  - memory/store boundaries
  - routing/governance/observability baseline
- steps:
  - read_core_entrypoints ✅
  - read_pipeline_and_worker_paths ✅
  - read_agent_runtime_and_m3_stages ✅
  - identify_determinism_breaks ✅
  - identify_consistency_gaps ✅
  - write_status_and_changelog ✅
- result:
  - top_weaknesses_identified: 5
  - active_focus_set: unified_run_envelope
  - runtime_code_changes: 0

---

## Recent Runs

### run_2026_04_09_production_alerting
- workflow_type: production_hardening / observability
- status: completed
- trace_id: tr_alerting_20260409
- owner: cursor
- scope:
  - `src/core/alerting.py` + `RunController.update_step` hook
  - `GET /api/v1/tenant/{tenant_id}/alerts`
  - monitoring badge + SideNav indicator
- tests: `tests/test_alerting.py`, `tests/test_api_tenant_alerts.py`

### run_2026_04_09_llm_quotas
- workflow_type: production_hardening / cost_governance
- status: completed
- trace_id: tr_llm_quotas_20260409
- owner: cursor
- scope:
  - `src/core/quotas.py` + Redis `tenant:{id}:llm_cost`
  - `LLMClient.invoke` pre-check + post-increment
  - `GET /api/v1/tenant/{tenant_id}/usage` + 429 `QuotaExceeded`
  - `llm_tenant_id` for `/ask` + existing agent bindings
- tests: `tests/test_quotas.py`, `tests/test_api_tenant_usage.py`

### run_2026_04_09_agent_llm_context_binding
- workflow_type: production_hardening / observability
- status: completed
- trace_id: tr_agent_llm_ctx_20260409
- owner: cursor
- scope:
  - `AgentExecutionEngine.execute_run` → `llm_run_context` bind/reset
  - `AgentScheduler.run_agent_and_log` → bind when `run_id` in `initial_context`
- tests: `tests/test_agent_llm_run_context.py`
- note: LLM timeline steps only when agent handler invokes `LLMClient` (not InsightAgentV2-only path)

### run_2026_04_09_direction_b_gemma_routing
- workflow_type: production_hardening / intelligence_routing
- status: completed
- trace_id: tr_direction_b_gemma_20260409
- owner: cursor
- scope:
  - `llm_router.select_model` + ROUTING_PROFILES
  - bulk → gemma4 (Ollama), reasoning → claude/groq/gemma by cost budget
  - Run timeline `llm_call_<route>` via `LLMClient` + `llm_run_context`
  - API `model` on tenant runs + run status; dashboard **model_used**
- env knobs: `LLM_COST_BUDGET`, `LLM_LATENCY_BUDGET`, `GEMMA4_OLLAMA_MODEL`, `INGEST_PIPELINE_LLM_ACK`
- steps:
  - router + client + context ✅
  - run_controller infer + list/status ✅
  - pipeline optional ack ✅
  - dashboard + apiClient ✅
  - tests ✅

### run_2026_04_09_001 (historical snapshot)
- workflow_type: ingest_event
- status: partial
- steps:
  - kafka_received ✅
  - mongo_write ✅
  - qdrant ❌
  - schema ⚠️
- error: qdrant timeout

### run_2026_04_09_002 (historical snapshot)
- workflow_type: ask
- status: completed
- latency: 1.2s
- model: reasoning-route (claude family)