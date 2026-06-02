# Verification strategy

For each **guarantee class**, define **proof** required. “Unverified” stays explicit until the listed artifact exists.

---

## G1 — Tenant-bound reads (`get_by_id` class)

| Mechanism | Unit | Integration | Notes |
| ---------- | ---- | ----------- | ----- |
| `get_by_id_for_tenant` rejects wrong tenant | Yes | — | Mock Mongo |
| Every API caller uses tenant-scoped primitive | Grep CI gate | OpenAPI contract tests | Fail build on `get_by_id(UUID` without `tenant` in same function scope **UNVERIFIED** quality of static grep |

**Proof bar:** 100% of `src/api` paths that return resource bodies filtered by JWT tenant in CI report.

---

## G2 — Tenant-bound mutations (governance, execute, DLQ)

| Mechanism | Unit | Integration |
| ---------- | ---- | ------------- |
| Cross-tenant approve → 403 | Yes | JWT A / event B |
| Execute with body tenant ≠ JWT → 403 | — | Yes |
| DLQ retry cross-tenant → 404/403 | Yes | Yes |

---

## G3 — Idempotency (Redis + Kafka)

| Mechanism | Unit | Integration | Chaos |
| ---------- | ---- | ------------- | ----- |
| Redis key includes `tenant_id` | Hash key format test | Two tenants same client key | — |
| Processor duplicate delivery | — | Publish same message twice; assert single side-effect counter | Redis flush mid-run **UNVERIFIED** unless manual |

---

## G4 — Webhook / bus honesty

| Mechanism | Integration |
| ---------- | ------------- |
| Broker down → non-2xx or explicit `ok:false` | docker stop kafka; curl webhook |

---

## G5 — Replay safety

| Mechanism | Integration |
| ---------- | ------------- |
| Stripe duplicate `event.id` | Replay same raw body twice; assert single lifecycle transition | Requires **recording** Stripe event ids in Postgres **if** you require hard proof—currently **define** `stripe_webhook_events` table **or** accept Stripe’s idempotency only **UNVERIFIED** |

---

## G6 — Authorization matrix (global)

| Mechanism | Tooling |
| --------- | ------- |
| Every route has declared auth dependency | Custom linter or `routes.json` generated test |
| OpenAPI securitySchemes | Generate from FastAPI and assert bearer on sensitive paths **UNVERIFIED** |

---

## G7 — Concurrency / load

| Guarantee | Proof |
| --------- | ----- |
| No lost updates on schema upsert under retry | **UNVERIFIED** — needs stress test with concurrent upserts + DB isolation level analysis |
| Consumer single-thread lag under load | Load test: sustained ingest TPS vs consumer lag SLO |

---

## G8 — Observability / audit reconstruction

| Guarantee | Proof |
| --------- | ----- |
| Failed run reconstructable | Manual drill: inject failure; grep `run_id` across logs + Redis snapshot |
| Audit trail complete | Compare Postgres `AuditLog` count to governance checks in load test **UNVERIFIED** |

---

## G9 — Fuzz / security

| Surface | Proof |
| ------- | ----- |
| UUID path params | Fuzz invalid UUIDs → 422, not 500 |
| Oversized webhook body | Limit `max_body` in server **UNVERIFIED** current limit |

---

## Unverified guarantees (explicit backlog)

1. **End-to-end exactly-once side effects** — not claimed; proof would require outbox + idempotent external APIs.  
2. **All LangChain / agent tool calls** tenant-scoped — requires per-tool audit.  
3. **Kafka ACL enforcement** — infra proof, not repo-only.
