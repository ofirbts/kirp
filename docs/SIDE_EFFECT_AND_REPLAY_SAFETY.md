# Side-effect and replay safety

Classifications: **SAFE** (duplicate work is benign or prevented), **PARTIAL** (mitigated but gaps remain), **DANGEROUS** (duplication or reordering can cause wrong external or cross-tenant effects).

## Webhook replay

| Source | Behavior | Class |
| ------ | -------- | ----- |
| Slack / WhatsApp / Notion | HTTP success does not prove Kafka publish; Slack/Stripe may retry POST | **DANGEROUS** for “exactly-once perception” |
| Stripe (`handle_webhook`) | No Stripe `event.id` dedup table in audited code; `update_tenant_lifecycle` overwrites same lifecycle field—**mostly idempotent** for same end state | **PARTIAL** (duplicate `created` retries are redundant writes; **UNVERIFIED** race with `deleted`) |

## Duplicate Kafka delivery

| Mechanism | Class | Notes |
| --------- | ----- | ----- |
| Redis `idempotency:*` TTL 1h | **PARTIAL** | After TTL, redelivery reprocesses |
| Mongo `get_by_id` skip if event id exists | **PARTIAL** | Helps only when same `event_id` replayed |
| `find_by_external_id` update path | **PARTIAL** | Notion-style upsert |

## Retry amplification

| Location | Bound | Class |
| -------- | ----- | ----- |
| `process_event` | `MAX_RETRIES=2` | **PARTIAL** | Bounded amplification per message |
| External LLM / HTTP in agents | tenacity may exist on some clients—**UNVERIFIED** all call sites | **UNVERIFIED** |
| Stripe | External retry policy | **PARTIAL** | Handler should be idempotent |

## External API duplication

| Action | Idempotency | Class |
| ------ | ----------- | ----- |
| Notion fetch in webhook | Per `page_id` in loop; Kafka emit unchecked | **PARTIAL** |
| M3 WhatsApp escalation | `pipeline.py` calls `send_m3_whatsapp_escalation` on requires_approval—**UNVERIFIED** duplicate send on pipeline retry | **UNVERIFIED** |

## Partial success

| Pattern | Class |
| ------- | ----- |
| Mongo written, Qdrant fails in pipeline | **PARTIAL** — inconsistent index vs store |
| Kafka emit succeeds, processor dies before Mongo | **PARTIAL** — at-least-once will retry |

## Compensating behavior

| Exists? | Evidence |
| ------- | -------- |
| Saga / compensating transactions | **Not observed** in audited pipeline—**UNVERIFIED** niche modules |
| DLQ | `EventStore.move_to_dlq` exists; **kafka_processor** terminal failure path does **not** call `move_to_dlq` in audited snippet—**PARTIAL** tooling without automatic poison routing |

## Idempotency key coverage

| Key surface | Tenant-scoped? |
| ----------- | -------------- |
| HTTP `Idempotency-Key` on ingest | Passed into envelope; Redis key `idem:{key}` **not tenant-prefixed** |
| M3 Mongo idempotency | `tenant_id` + `user_id` + key in `memory_mongo.py` | **Yes** |

---

## Summary table

| Scenario | Class |
| -------- | ----- |
| JWT ingest + Kafka down | **SAFE** for corruption (503); **SAFE** for no partial bus write |
| Webhook + Kafka down | **DANGEROUS** (false success signal) |
| Redis idempotency lost | **DANGEROUS** under at-least-once |
| Governance approve without tenant check | **DANGEROUS** (authorization) |
| Stripe subscription lifecycle replay | **PARTIAL** |
| Qdrant search with tenant filter | **SAFE** for isolation (not for “no wrong answer”) |
