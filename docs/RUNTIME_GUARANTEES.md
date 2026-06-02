# Runtime guarantees matrix

Each row states **semantics backed by code inspection**. Where proof would require load tests, fuzzing, or full route enumeration, the cell is **UNVERIFIED** (explicit uncertainty increases trust).

## Legend

| Term | Meaning in this doc |
| ---- | ------------------- |
| **at-least-once** | Work may run more than once for one logical submission (Kafka + uncommitted offset). |
| **best-effort** | Success not guaranteed; failures may be silent or soft-degraded. |
| **effectively-once** | Intended duplicate suppression via idempotency keys + storage checks; **not** formal exactly-once. |

---

## Critical operations

| Operation | Delivery | Idempotency | Ordering | Retries | Timeout / cancel | Persistence | Audit | Evidence |
| --------- | -------- | ----------- | -------- | ------- | ---------------- | ------------- | ----- | -------- |
| `POST /api/v1/ingest` (JWT) | **at-most-once** to Kafka if `emit` returns true (single produce+flush attempt in `KafkaEventAgent`); **zero** delivery if producer nil / emit false → **503** | New `run_id` per request unless caller reuses same JWT session logic; **no** server-side dedup of duplicate HTTP retries **UNVERIFIED** for identical body | **None** guaranteed across events (single partition key by event type key in producer—**ordering not per tenant**): `kafka_event_agent.py` key=`event.type` | None in API path | `producer.flush(timeout=5.0)`; no request cancellation hook | Run state in Redis **best-effort**; Kafka record if emitted | `log_json` + run steps | `main.py`, `kafka_event_agent.py` |
| Webhook → `_ingest_one` | **best-effort** to Kafka; **no** check of `emit` return → **at-least-zero** client-visible delivery guarantee | Same as ingest if emit checked; **currently** no proof of publish | **None** | None | flush 5s in agent | **None** proven if emit fails | Partial logs only | `v1_ingestion.py` |
| Kafka consumer `process_event` | **at-least-once** (commit after success only) | Redis `idempotency:{key}` TTL **3600s**; keys **`idem:{explicit}`** and **`run:{run_id}`** etc. **omit `tenant_id` prefix** → cross-tenant collision **possible** if same idempotency key reused across tenants; **UNVERIFIED** production rate | Single consumer per group **per partition** order; topic has partitions=3 (`kafka_processor` admin)—**global order not per tenant** | **MAX_RETRIES=2**, backoff `RETRY_DELAY * (retry_count+1)` | Poll `timeout=1.0`; no asyncio cancel of in-flight `process_event` **UNVERIFIED** for worker shutdown | Mongo/Postgres/Qdrant per pipeline | `log_json` + metrics | `kafka_processor.py` |
| `EventPipeline.run` | **best-effort** partial (Mongo may succeed, Qdrant fail—logged) | Event `id` can be supplied for replay path | **None** vs other tenants’ events | No automatic outer retry in `pipeline.py` excerpt | No pipeline-level timeout wrapper **UNVERIFIED** full call chain | Mongo insert/updates; Qdrant upsert try/except | Governance deny → `PermissionError`; audit `log_audit` **best-effort** Postgres | `pipeline.py`, `governance.py` |
| `RAGEngine.search` / upsert | **best-effort** | N/A search; upsert by point id | **UNVERIFIED** under concurrent upserts | None in method | **UNVERIFIED** full Qdrant client timeouts | Qdrant payload includes `tenant_id` | Metrics labels include `tenant_id` | `rag_engine.py` |
| `GovernanceEngine.check` | **best-effort** | N/A | N/A | None | httpx **5.0s** OPA POST | None | **best-effort** `log_audit` | `governance.py` |
| `RunController` updates | **best-effort** Redis; in-memory mirror | Same `run_id` create returns existing id without tenant equality enforcement beyond log warning | **UNVERIFIED** multi-writer | Redis reconnect backoff | No op timeout per command **UNVERIFIED** | Redis hash + optional legacy key | Steps visible via GET run API | `run_controller.py` |
| `POST /governance/approve/{event_id}` / `reject` | **at-most-once** per call | New resolution `Event` id each call—duplicate approve creates **duplicate resolution events** **UNVERIFIED** downstream dedup | N/A | None | None | Mongo `ingest` | Writes resolution event | `governance.py` |
| `EventStore.get_by_id` | N/A | N/A | N/A | N/A | N/A | Read | N/A | **No `tenant_id` filter**—`find_one({"_id": str(event_id)})` |
| Stripe webhook | **at-least-once** (Stripe retries) | **UNVERIFIED** idempotency of `handle_webhook` | N/A | Stripe-controlled | N/A | Depends on handler | `log_json` | `main.py`, `stripe_service` **UNVERIFIED** full handler |

---

## Transaction boundaries

| Unit | Boundary | Uncertainty |
| ---- | ---------- | ------------ |
| Mongo single `insert_one` | Per document atomic | Pipeline not a single multi-doc transaction with Qdrant. |
| Postgres `AuditLog` commit | Single session commit in `log_audit` | Exceptions swallowed after log. |
| Kafka offset commit | After successful `process_event` | Failure between side effects and commit → **duplicate side effects** unless idempotent. |

---

## Explicit non-guarantees

1. **No exactly-once end-to-end** across Kafka + Mongo + Qdrant + Postgres without distributed transactions (not used).
2. **No request-level correlation ID** on all HTTP responses (**UNVERIFIED** any middleware not in prior audit).
3. **Governance approve/reject** does not compare `request.state.user.tenant_id` to `ev.tenant_id` in router handler—**authorization gap** separate from storage filter (see `TENANT_ISOLATION_REVIEW.md`).

---

## UNVERIFIED bucket (honest backlog)

- Duplicate **HTTP** retry of `/api/v1/ingest` with same `Idempotency-Key` header: **UNVERIFIED** whether any path dedups at API layer (processor has Redis/Mongo partial paths).
- **Poison message** after `MAX_RETRIES`: offset stuck vs skip vs DLQ—**UNVERIFIED** full behavior for non-parse errors.
- **Worker graceful shutdown**: in-flight `process_event` on SIGTERM—**UNVERIFIED**.
