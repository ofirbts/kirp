# Skeptical staff review — production approval lens

**Reviewer stance:** principal engineer, production approval gate. **No reputation management**—only whether risks are visible, bounded, and acceptable for the intended blast radius.

---

## Strongest engineering signals

1. **Kafka + worker path is real**, not stubbed: consumer loop, conditional offset commit, structured logging, and topic administration code exist (`kafka_processor.py`, `integrations.py`).
2. **Multi-tenant discipline appears in core stores**: Qdrant filters require `tenant_id`; Mongo `list` rejects careless `*`; schema engine SQL scopes `tenant_id`.
3. **Explicit failure mode on JWT ingest** when the bus is unavailable (**503**)—better than silent drop.
4. **Operational truth docs** now exist (`RUNTIME_REALITY_MATRIX`, `FAILURE_SEMANTICS`, `RUNTIME_GUARANTEES`, this wave)—the org can argue from evidence instead of slides.

## Strongest operational signals

1. **RunController** step model gives a concrete timeline when Redis works.
2. **`log_json`** on ingest and processor paths supports log aggregation queries.
3. **Deploy compose** can stand a full pipeline for local prod-like debugging.

## Weakest guarantees

1. **Authorization vs storage:** `get_by_id` is not tenant-scoped; **governance approve/reject** does not bind JWT tenant to the loaded event—this is a **showstopper-class** issue for multi-tenant SaaS if those routes are exposed to normal users.
2. **Webhook vs Kafka:** success responses without verifying publish—operators cannot trust HTTP alone.
3. **Redis idempotency keys** without tenant prefix—collision and cross-tenant suppression risk.
4. **No distributed tracing**; worker metrics disabled in default compose—**flight recorder** is thin during incidents.

## Architectural honesty score

**8 / 10** — Documentation now admits dead paths, doc drift, and webhook gaps. Remaining gap is **fixing** known authorization issues, not hiding them.

## Operational maturity score

**5 / 10** — Good logs on hot paths; missing DLQ automation, poison handling, universal request IDs, and guaranteed observability on the worker.

## Reviewer trust score

**7 / 10** — Honest write-ups increase trust; unresolved **governance IDOR** and **webhook false-positive** reduce it materially.

## Production survivability score

**5 / 10** — Survives happy path and single-region dependency bumps; **does not yet survive** adversarial multi-tenant access patterns or poisoned partitions without manual ops.

## Most dangerous unknowns

1. Full enumeration of **API routes** that accept resource IDs without tenant re-check (`get_by_id` pattern).
2. **Agent / tool** paths that call external APIs without idempotency keys—**UNVERIFIED** blast radius.
3. **Concurrent schema writes** under Kafka replay—**UNVERIFIED** conflict behavior.

## What blocks full production confidence

1. Close **tenant authorization gaps** on any route that loads a resource by UUID without `tenant_id` guard.
2. Make **webhook** publish failures visible (check `emit`, return 503/502, or enqueue reliably).
3. **Prefix idempotency keys** with `tenant_id` (and ideally `space_id` where relevant).
4. **Operationalize poison messages** (DLQ from processor or skip+alert policy).

## What inspires confidence

- The team **named** the weak spots instead of obscuring them—this is rare and valuable.
- Core vector and list queries **encode** tenant isolation as mandatory filters.

## What still feels prototype-like

- Governance HTTP routes without JWT tenant binding on mutate.
- Single-topic Kafka without per-tenant isolation story beyond payload validation.
- Relying on Redis TTL idempotency alone for correctness under redelivery.

---

## Final sentence

**Would I approve this for “critical multi-tenant workflows” today?** **No**—not until governance mutation routes and any `get_by_id` exposure are tenant-authorized and webhook Kafka failures are client-visible. **Would I approve for a controlled internal pilot with trusted users and ops monitoring Kafka lag?** **Yes**, with written runbooks for Redis/Kafka outages and explicit “do not use webhooks as sole SoR without lag checks.”
