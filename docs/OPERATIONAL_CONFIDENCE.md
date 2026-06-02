# Operational confidence layer

What you can **prove** during an incident without reading the whole repo. Status: **exists / partial / missing / dangerous**.

## Correlation and tracing

| Capability | Status | Evidence |
| ---------- | ------ | -------- |
| Request-scoped trace IDs on ingest | **exists** | `trace_id` generated per `POST /api/v1/ingest`; returned in JSON (`main.py`). |
| `trace_id` on events | **exists** | `Event.trace_id`, pipeline `log_json` fields. |
| HTTP `X-Request-Id` / W3C traceparent middleware | **missing** | No middleware in `main.py` audit that stamps incoming request IDs to all responses. |
| Cross-service trace propagation to Kafka | **partial** | Envelope carries `trace_id`; consumer logs `log_json` with same. |

## Structured logging

| Capability | Status | Evidence |
| ---------- | ------ | -------- |
| JSON-shaped critical logs | **exists** | `src/core/structured_logging.py` `log_json`. |
| Nullable identity keys | **exists** | `tenant_id`, `run_id`, `trace_id` explicit null in JSON. |

## Run lifecycle visibility

| Capability | Status | Evidence |
| ---------- | ------ | -------- |
| Redis-backed run hash | **exists** | `RunController` keys `tenant:{tid}:{run_id}`. |
| Step updates from API + processor | **exists** | `update_step` from `main.py` ingest + `kafka_processor`. |
| Multi-replica consistency | **dangerous** | Redis loss → in-memory only per process; no lease model. |

## Retry visibility

| Capability | Status | Evidence |
| ---------- | ------ | -------- |
| Processor bounded retries | **exists** | `MAX_RETRIES`, `log_json` `kafka_processor_retrying`. |
| Client-visible retry guidance | **missing** | 503 text static; no `Retry-After`. |

## Policy decision visibility

| Capability | Status | Evidence |
| ---------- | ------ | -------- |
| OPA HTTP outcome logged | **partial** | Exceptions logged; allow/deny folded into pipeline step updates. |
| Centralized policy decision audit stream | **partial** | `log_audit` Postgres + stdout; failures swallowed with error log. |

## Audit trail guarantees

| Capability | Status | Evidence |
| ---------- | ------ | -------- |
| Mongo event history | **exists** | EventStore writes. |
| Postgres `AuditLog` | **partial** | `governance.log_audit` try/except—**best-effort**. |

## Tenant isolation guarantees

| Capability | Status | Evidence |
| ---------- | ------ | -------- |
| JWT ingest rejects empty user | **exists** | `403` path. |
| Webhooks ignore body tenant | **exists** | Env-only routing in `v1_ingestion.py`. |
| Processor rejects bad tenant payload | **exists** | `validate_ingest_tenant_context`. |

## Side-effect recording

| Capability | Status | Evidence |
| ---------- | ------ | -------- |
| Typed commands / approvals narrative | **partial** | Governance + agents; not uniformly enforced on every HTTP path—route-level review required. |

## Metrics

| Capability | Status | Evidence |
| ---------- | ------ | -------- |
| Prometheus client usage | **exists** | `src/observability/metrics.py`; namespaces `kirp_kafka`, `kirp_pipeline`, etc. |
| Processor metrics disabled in compose | **exists** | `DISABLE_PROMETHEUS=1` on `kirp-agent-processor` in `deploy/docker-compose.prod.yml`. |

## Dangerous gaps (explicit)

1. **Webhook success vs Kafka publish** — HTTP 200 possible while `emit` failed (**missing** client-visible failure).
2. **OPA unset** — governance **fail-open** (**dangerous** if operators believe policies always enforce).
3. **Redis optional for dedup** — duplicate processing risk (**dangerous** under redelivery + no Redis).
4. **`deploy/README.md` Kafka claim** — contradicts `deploy/docker-compose.prod.yml` (**documentation risk** → operator error).

## Minimal hardening backlog (non-cosmetic)

1. Check `KafkaEventAgent.emit` return in **all** ingestion entrypoints or return 503 on failure.
2. Add request correlation middleware (`X-Request-Id` echo + log binding).
3. Align `deploy/README.md` §4c with actual compose services.
4. Document OPA fail-open explicitly in prod runbooks until startup gate exists.
