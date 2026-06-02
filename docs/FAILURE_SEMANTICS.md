# Failure Semantics — KIRP runtime behavior

Operations memo: **what actually happens** when dependencies misbehave. Unless noted, behavior is inferred from `src/` as audited alongside `docs/RUNTIME_REALITY_MATRIX.md`.

---

## 1. Kafka unavailable (broker down, DNS wrong, library missing)

**Detection**

- `get_kafka_producer()` returns `None` if `confluent-kafka` import fails (`integrations.py`).
- `KafkaEventAgent.emit` logs `kafka_emit_failed` / `producer_unavailable` and returns `False`.

**User-visible**

- `POST /api/v1/ingest` (JWT): **503** `"Event bus unavailable; ingest not published"`; run step `kafka_emitted` → **failed** (`main.py`).
- Webhook routes (`v1_ingestion.py`): **emit return value not checked** → HTTP **200** with `ok: true` / `processed` counts may **overstate** delivery (**fail-open to the client**).

**Consumer**

- `kafka_processor.consume_forever` loops: consumer `None` → sleep `CONNECT_RETRY_SEC` and retry.

**Idempotency / offsets**

- Processor: failed handling → **no commit** → redelivery at-least-once.

**Observability**

- `log_json` events: `ingest_api_emit_failed`, `kafka_emit_failed`, `kafka_processor_failed`, metrics `kirp_kafka_*` when Prometheus enabled.

**Audit**

- No durable audit of “accepted but not published” for webhooks unless added separately.

---

## 2. Duplicate events (Kafka redelivery, client retries)

**Detection**

- Redis key `idempotency:{key}` in processor (`_check_idempotency`); TTL `IDEMPOTENCY_TTL` 3600s.
- Secondary: existing Mongo `event_id` or `find_by_external_id` paths in `kafka_processor.process_event`.

**Degradation**

- If Redis unavailable: Redis idempotency **skipped** → reliance on Mongo checks; **window for duplicate processing widens**.

**Retry semantics**

- API ingest: client retry may create **new** `run_id` each attempt unless client implements higher-level dedup.

**Fail-open vs fail-closed**

- JWT ingest path: **fail-closed** if Kafka cannot take the message.
- Webhooks: **fail-open** on publish success reporting.

---

## 3. Redis outage (run state + idempotency)

**RunController** (`run_controller.py`)

- Connection ping fails after N attempts → 15s backoff; operations continue with **in-process** `run_states` dict.
- Hard init failure sets `_redis_hard_disabled` → **permanent in-memory** for that process.

**Processor idempotency**

- `get_redis_async` None → `_check_idempotency` / `_mark_processed` no-op → **no cross-process dedup**.

**Lock loss**

- There is **no distributed lock** in the audited path for pipeline execution; “lock loss” mainly means **lost run visibility** across replicas and **idempotency weakening**, not mutex corruption.

---

## 4. OPA unavailable

**`OPA_URL` unset**

- `GovernanceEngine._enabled` is false → `check` returns **allowed=True**, reason `Governance disabled (no OPA)` (**fail-open**).

**`OPA_URL` set but OPA HTTP error / timeout**

- Non-200 → `allowed=False`, `requires_approval=True` (**fail-closed** for writes that respect governance).
- Exceptions (network) → same fail-closed path; logged `Governance check failed`.

**Observability**

- Pipeline logs governance deny as `PermissionError` with reason string.

**Audit**

- `log_audit` best-effort to Postgres; failure logged; stdout line still emitted.

---

## 5. Vector DB (Qdrant) unavailable

**RAG engine init**

- `get_rag_engine` in `main.py` can raise on connect failure → `/health` returns **503**.

**Pipeline**

- Embed/upsert wrapped in try/except: failures logged; event may still be stored in Mongo depending on branch (**partial write**).

**`/api/v1/ask`**

- Explicit soft response if RAG unavailable: text answer explains Qdrant missing (**degraded UX, HTTP 200**).

---

## 6. LLM timeout / provider errors

**Client**

- `src/core/llm_client.py` uses `httpx.AsyncClient(timeout=60.0)` for at least one path.

**Semantics**

- Exceptions propagate to caller; agent/pipeline layers may log and fail the current unit of work.

**Retry storms**

- Kafka processor retries failed `process_event` up to **MAX_RETRIES=2** with backoff **1s × attempt**—bounded, not exponential to infinity.
- No global circuit breaker found in audit—**retry amplification risk** if downstream always errors.

---

## 7. Partial orchestration failure

**Pipeline steps**

- Governance can fail before Mongo write → **no event** persisted for that attempt.
- Mongo write may succeed while Qdrant fails → **split brain** between blob store and vectors until repaired.

**Run steps**

- `RunController.update_step` failures are logged; Kafka processor marks `kafka_failed` on terminal failure after retries.

---

## 8. Tenant routing issues

**JWT paths**

- Tenant comes from auth context; mismatch with body defaults removed on ingest (`main.py` docstring).

**Webhooks**

- Tenant **only** from env vars (`SLACK_WEBHOOK_*`, `WHATSAPP_WEBHOOK_*`, `NOTION_WEBHOOK_*`) per route docstrings—**fail-closed** against body-supplied tenant spoofing.

**Processor**

- `validate_ingest_tenant_context` rejects invalid / missing `tenant_id` or `user_id` → **False** return path; metrics `invalid_tenant` / `missing_user_id`.

---

## 9. Webhook duplication

**Slack**

- Parser produces events; each may call `_ingest_one` independently.

**Dedup**

- Relies on downstream Kafka idempotency + Mongo keys; **no** HMAC replay window in code beyond integration-specific parsing.

---

## 10. Downstream backpressure

**Kafka consumer**

- Single-threaded poll loop; `process_event` awaited; slow pipeline **blocks** consumption (no parallel batch size in audited loop).

**Producer**

- `flush(timeout=5)` in `KafkaEventAgent`—bounded wait.

**API**

- No explicit per-tenant rate limit on ingest beyond onboarding IP RL (`main.py`).

---

## 11. Postgres / Mongo hard failures

**Prod env**

- `validate_prod_env` requires `DATABASE_URL`, `REDIS_URL`, `STRIPE_SECRET_KEY` in production—API startup **raises** if missing.

**Lazy clients**

- Event store connect failures on first use can surface as 500s on routes depending on exception mapping.

---

## Summary table

| Scenario | Primary fail mode | Client impact | Dedup | Audit |
| -------- | ----------------- | ------------- | ----- | ----- |
| Kafka down + JWT ingest | fail-closed | 503 | N/A | run step failed |
| Kafka down + webhook | fail-open | 200 OK possible | weak | weak |
| OPA down + URL set | fail-closed | 403/500 depending on route | N/A | policy deny path |
| OPA missing + URL unset | fail-open | writes allowed | N/A | risk accepted |
| Redis down | degraded | runs/idempotency unreliable | weakened | partial |
| Qdrant down | partial/degraded | health 503 or ask soft-fail | N/A | N/A |
