# Observability review

Maps **signals** to **code** and answers **operator questions** honestly.

## Logs

| Type | Location | Structure | Tenant visible |
| ---- | -------- | --------- | ---------------- |
| App logger | `logging` throughout | Mix of format strings and `log_json` | Often in `log_json` fields |
| `log_json` | `src/core/structured_logging.py` | JSON line with `event`, `tenant_id`, `run_id`, `trace_id` | **Yes** when passed |

**Gap:** no universal middleware stamping `request_id` on every request/response in audited `main.py` stack.

## Metrics

| Collector | Namespace | Disabled when |
| --------- | --------- | ------------- |
| `MetricsCollector` | `kirp_kafka`, `kirp_pipeline`, etc. | `DISABLE_PROMETHEUS=1` or missing `prometheus_client` |
| Worker compose | `DISABLE_PROMETHEUS=1` on `kirp-agent-processor` | Processor metrics **off** in default deploy file |

## Traces

| System | Status |
| ------ | ------ |
| OpenTelemetry / distributed traces | **Not found** in grep of `src/` for opentelemetry |

## Correlation IDs

| ID | Propagation |
| -- | ----------- |
| `trace_id` | Generated on ingest; embedded in payload and logs; **not** proven as HTTP response header on all routes |
| `run_id` | Returned to client on ingest; Redis run hash |
| `event_id` | UUIDv4 on canonical path |
| Stripe `trace_id` in logs | Uses Stripe event id when present |

## Operational questions

### Can an operator reconstruct a failed run?

**PARTIAL.** If Redis healthy: `GET` run APIs (see `main.py` run visibility) + `log_json` lines with same `run_id`/`trace_id`. If Redis down and process restarted: **in-memory state lost** — **cannot** fully reconstruct.

### Can duplicate execution be proven?

**PARTIAL.** Kafka consumer does not commit on failure → lag grows; Redis idempotency hit logs “already processed”. **Cannot** prove duplicates without log retention + Redis key inspection (TTL expires keys).

### Can cross-service flow be traced?

**PARTIAL.** `trace_id` in Kafka payload and logs links API → processor **if** logs centralized and clocks trustworthy. **No** trace IDs in HTTP headers standard across services.

### Can tenant incidents be isolated?

**PARTIAL.** `log_json` includes `tenant_id` on many paths; metrics label `tenant_id` on RAG. **Gap:** grep-only incident response still possible but **not** a dedicated per-tenant dashboard in code audit.

### Can audit history be reconstructed?

**PARTIAL.** Postgres `AuditLog` when `log_audit` succeeds; failures only stdout. Mongo events are append-heavy. **No** single “audit export” API verified in this pass.

## Queue visibility

| Signal | Exists? |
| ------ | ------- |
| Kafka consumer lag | **External** (Kafka tooling), not embedded in API health |
| `kafka_errors` metrics | Yes when Prometheus enabled |

## Failure visibility

| Failure | Visible how |
| ------- | ----------- |
| Ingest bus down | HTTP 503 + `ingest_api_emit_failed` |
| Processor exception | Logs + run step `kafka_failed` |
| OPA deny | Pipeline error + governance reason string |

---

## Bottom line

**Strong:** JSON logs on critical paths with tenant/run/trace fields.

**Weak:** No distributed tracing; Prometheus optional/disabled on worker; no guaranteed request ID; audit persistence best-effort.

**Dangerous:** Assuming logs alone prove side effects without correlating Kafka offset lag and Mongo writes.
