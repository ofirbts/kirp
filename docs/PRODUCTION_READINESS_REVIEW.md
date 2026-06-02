# Production readiness review

Synthesis after `RUNTIME_REALITY_MATRIX`, `FAILURE_SEMANTICS`, `ARCHITECTURE_TRACEABILITY`, and `OPERATIONAL_CONFIDENCE`. Written for a **skeptical staff engineer** deciding whether to bet a critical workflow on this codebase **as audited**—not as a product marketing review.

## Architecture strengths

- **Clear primary path:** JWT `POST /api/v1/ingest` → Kafka → `kafka_processor` → EventRegistry → EventPipeline → stores is **traceable and fail-closed** when the bus is down (**503**).
- **Duplicate reality acknowledged in code:** Redis idempotency keys + Mongo id checks + offset commit rules show awareness of at-least-once Kafka.
- **Webhook tenant model:** Env-only tenant routing avoids trusting attacker-controlled JSON on public URLs.
- **Governance hook exists:** OPA integration is real (HTTP to `/v1/data/kirp/governance/allow`), not a stub, when `OPA_URL` is set.

## Operational strengths

- **RunController step trail** ties API acceptance to processor progress when Redis is healthy.
- **`log_json`** gives grep-friendly JSON for major failure classes (`ingest_api_emit_failed`, `kafka_processor_failed`, etc.).
- **Deploy compose** wires the async path explicitly (Kafka + worker + OPA + Qdrant)—good for local prod-like debugging.

## Failure handling maturity

- **Strong:** JWT ingest Kafka outage surfaces as **503** with structured logs and run step failure.
- **Weak:** Webhook paths **do not** surface Kafka publish failure—**operational lie risk** (HTTP 200 while nothing entered the bus).
- **Mixed:** OPA **fail-open** when disabled vs **fail-closed** when misbehaving—operators must understand which mode they are in.
- **Bounded:** Processor retries capped at 2—avoids infinite loops; may drop poison messages after retries (offset not committed → stuck partition risk for permanent poison—**unverified** handling).

## Trust boundaries

- **Trust JWT + RunController** for synchronous API semantics.
- **Do not trust** webhook HTTP 200 as proof of pipeline execution until emit results are checked.
- **Do not trust** cross-replica run visibility without Redis.

## Weakest production assumptions

1. Redis available for **dedup + run state** in multi-instance deployments.
2. Operators read **compose file**, not stale README prose, for whether Kafka exists.
3. Single consumer throughput adequate (poll loop processes one message flow serially in the audited loop structure).

## Hidden coupling risks

- **Lazy singletons** in `main.py` (`get_event_store`, `get_rag_engine`, …) tie health and first-request latency to cold-start behavior.
- **RAG + Mongo** coupled in `/health`: partial infra outages flip health to 503 even if some routes could serve.
- **LangChain stack** in requirements increases dependency surface for RAG paths—security and reproducibility cost.

## Scalability assumptions

- Kafka topic `kirp-events` single-topic fan-in; partition count and consumer group scaling **not documented in code audit**.
- Redis TTL idempotency (1h) means **replay after TTL** can reprocess—acceptable only if downstream remains idempotent.

## Tenant isolation confidence

- **Medium-high** on JWT-scoped routes where `get_tenant_context` is enforced.
- **High** on webhooks for **spoof resistance** (env routing).
- **Lower** for **data plane** guarantees without a full review of every `tenant_id` filter in Mongo/Qdrant queries—recommended targeted audit beyond this pass.

## Observability maturity

- **Medium:** good structured events on hot paths; no universal request ID middleware; Prometheus optional/disabled on worker in default compose.

## Deployment confidence

- **Medium:** `deploy/docker-compose.prod.yml` is coherent; **documentation drift** (`deploy/README.md` Kafka claim) **lowers** confidence until fixed.

## Current bottlenecks

- Synchronous pipeline work in consumer loop → **head-of-line blocking**.
- LLM calls inside agent paths can stall processing—timeouts exist (60s) but multiply wall clock under retry.

## Biggest unknowns (require deeper pass)

- Full **tenant filter** coverage across all Mongo aggregations and Qdrant filters.
- **Poison message** policy after max retries (DLQ not seen in audit).
- **Exact** Stripe + onboarding concurrency behavior under duplicate webhooks.

---

## Scores (0–10, brutal)

| Metric | Score | Rationale |
| ------ | ----- | --------- |
| **Production readiness** | **6** | Core path exists; webhook/Kafka legibility gap and OPA fail-open are production-grade risks. |
| **Operational trust** | **6** | Good logs for JWT ingest; missing publish verification on webhooks undermines incident response trust. |
| **Reviewer trust** | **7** | This audit package is honest about gaps; stale deploy README hurts external reviewer confidence until corrected. |

## Verdict

**Defensible for controlled rollouts** where:

- JWT ingest is the **only** critical ingress, or webhooks are monitored via **Kafka lag / processor metrics**, not HTTP 200.
- Operators explicitly configure **OPA_URL** if policy is mandatory.
- Redis is treated as **required** for correct dedup and run visibility in scaled deployments.

**Not yet defensible** as “HTTP 200 means work happened” across **all** ingestion surfaces without code changes.
